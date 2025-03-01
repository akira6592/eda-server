#  Copyright 2023 Red Hat, Inc.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
import logging

from django.conf import settings
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as defaultfilters
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from aap_eda.api import exceptions as api_exc, filters, serializers
from aap_eda.core import models
from aap_eda.core.enums import Action, ActivationStatus, ResourceType
from aap_eda.tasks.ruleset import (
    activate_rulesets,
    deactivate,
    deactivate_rulesets,
)

logger = logging.getLogger(__name__)


def handle_activation_create_conflict(activation):
    activation_dependent_objects = [
        (
            models.DecisionEnvironment,
            "decision_environment",
            activation.get("decision_environment_id"),
        ),
        (models.Project, "project", activation.get("project_id")),
        (models.Rulebook, "rulebook", activation.get("rulebook_id")),
        (models.ExtraVar, "extra_var", activation.get("extra_var_id")),
    ]
    for object_model, object_name, object_id in activation_dependent_objects:
        if object_id is None:
            continue
        object_exists = object_model.objects.filter(pk=object_id).exists()
        if not object_exists:
            raise api_exc.Unprocessable(
                detail=f"{object_name.capitalize()} with ID={object_id}"
                " does not exist.",
            )
    raise api_exc.Unprocessable(detail="Integrity error.")


@extend_schema_view(
    destroy=extend_schema(
        description="Delete an existing Activation",
        responses={
            status.HTTP_204_NO_CONTENT: OpenApiResponse(
                None,
                description="The Activation has been deleted.",
            ),
        },
    ),
)
# REVIEW(cutwater): Since this class implements `create` method,
#   the `CreateModelMixin` is redundant.
class ActivationViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = models.Activation.objects.all()
    serializer_class = serializers.ActivationSerializer
    filter_backends = (defaultfilters.DjangoFilterBackend,)
    filterset_class = filters.ActivationFilter

    rbac_resource_type = None
    rbac_action = None

    @extend_schema(
        request=serializers.ActivationCreateSerializer,
        responses={
            status.HTTP_201_CREATED: serializers.ActivationReadSerializer
        },
    )
    def create(self, request):
        serializer = serializers.ActivationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            response = serializer.create(
                serializer.validated_data, request.user
            )
        except IntegrityError:
            handle_activation_create_conflict(serializer.validated_data)

        response_serializer = serializers.ActivationSerializer(response)
        activation = self._get_activation_dependent_objects(
            response_serializer.data
        )
        activation["rules_count"] = 0
        activation["rules_fired_count"] = 0

        if response.is_enabled:
            activate_rulesets.delay(
                is_restart=False,
                activation_id=response.id,
                deployment_type=settings.DEPLOYMENT_TYPE,
                ws_base_url=settings.WEBSOCKET_BASE_URL,
                ssl_verify=settings.WEBSOCKET_SSL_VERIFY,
            )

        return Response(
            serializers.ActivationReadSerializer(activation).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        responses={status.HTTP_200_OK: serializers.ActivationReadSerializer},
    )
    def retrieve(self, request, pk: int):
        response = super().retrieve(request, pk)
        activation = self._get_activation_dependent_objects(response.data)
        (
            activation["rules_count"],
            activation["rules_fired_count"],
        ) = self._get_rules_count(activation["ruleset_stats"])

        return Response(serializers.ActivationReadSerializer(activation).data)

    @extend_schema(
        description="List all Activations",
        request=None,
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                serializers.ActivationListSerializer(many=True),
                description="Return a list of Activations.",
            ),
        },
    )
    def list(self, request):
        # TODO: No need to call monitor when a scheduler is in place
        from aap_eda.tasks.ruleset import monitor_activations

        monitor_activations()

        response = super().list(request)
        activations = []
        if response and response.data:
            activations = response.data["results"]

        for activation in activations:
            (
                activation["rules_count"],
                activation["rules_fired_count"],
            ) = self._get_rules_count(activation["ruleset_stats"])

        serializer = serializers.ActivationListSerializer(
            activations, many=True
        )

        return self.get_paginated_response(serializer.data)

    def perform_destroy(self, activation):
        instances = models.ActivationInstance.objects.filter(
            activation_id=activation.id
        )
        for instance in instances:
            deactivate_rulesets.delay(instance.id, settings.DEPLOYMENT_TYPE)
        super().perform_destroy(activation)

    @extend_schema(
        description="List all instances for the Activation",
        request=None,
        responses={
            status.HTTP_200_OK: serializers.ActivationInstanceSerializer(
                many=True
            ),
        },
        parameters=[
            OpenApiParameter(
                name="id",
                type=int,
                location=OpenApiParameter.PATH,
                description="A unique integer value identifying this rulebook.",  # noqa: E501
            )
        ],
    )
    @action(
        detail=False,
        queryset=models.ActivationInstance.objects.order_by("id"),
        filterset_class=filters.ActivationInstanceFilter,
        rbac_resource_type=ResourceType.ACTIVATION_INSTANCE,
        rbac_action=Action.READ,
        url_path="(?P<id>[^/.]+)/instances",
    )
    def instances(self, request, id):
        activation_exists = models.Activation.objects.filter(id=id).exists()
        if not activation_exists:
            raise api_exc.NotFound(
                code=status.HTTP_404_NOT_FOUND,
                detail=f"Activation with ID={id} does not exist.",
            )

        activation_instances = models.ActivationInstance.objects.filter(
            activation_id=id
        )
        filtered_instances = self.filter_queryset(activation_instances)
        result = self.paginate_queryset(filtered_instances)
        serializer = serializers.ActivationInstanceSerializer(
            result, many=True
        )
        return self.get_paginated_response(serializer.data)

    @extend_schema(
        description="Enable the Activation",
        request=None,
        responses={
            status.HTTP_204_NO_CONTENT: OpenApiResponse(
                None,
                description="Activation has been enabled.",
            ),
            status.HTTP_409_CONFLICT: OpenApiResponse(
                None,
                description="Activation not enabled do to current activation "
                "status",
            ),
        },
    )
    @action(methods=["post"], detail=True, rbac_action=Action.ENABLE)
    def enable(self, request, pk):
        activation = get_object_or_404(models.Activation, pk=pk)
        if activation.is_enabled:
            return Response(status=status.HTTP_204_NO_CONTENT)

        if activation.status in [
            ActivationStatus.STARTING,
            ActivationStatus.STOPPING,
            ActivationStatus.PENDING,
            ActivationStatus.RUNNING,
            ActivationStatus.UNRESPONSIVE,
        ]:
            return Response(status=status.HTTP_409_CONFLICT)

        logger.info(f"Now enabling {activation.name} ...")

        activation.is_enabled = True
        activation.failure_count = 0
        activation.status = ActivationStatus.PENDING
        activation.save(
            update_fields=[
                "is_enabled",
                "failure_count",
                "status",
                "modified_at",
            ]
        )

        job = activate_rulesets.delay(
            is_restart=False,
            activation_id=pk,
            deployment_type=settings.DEPLOYMENT_TYPE,
            ws_base_url=settings.WEBSOCKET_BASE_URL,
            ssl_verify=settings.WEBSOCKET_SSL_VERIFY,
        )

        activation.current_job_id = job.id
        activation.save(update_fields=["current_job_id"])

        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        description="Disable the Activation",
        request=None,
        responses={
            status.HTTP_204_NO_CONTENT: OpenApiResponse(
                None,
                description="Activation has been disabled.",
            ),
        },
    )
    @action(methods=["post"], detail=True, rbac_action=Action.DISABLE)
    def disable(self, request, pk):
        activation = get_object_or_404(models.Activation, pk=pk)

        if activation.is_enabled:
            activation.status = ActivationStatus.STOPPING
            activation.is_enabled = False
            activation.save(
                update_fields=["is_enabled", "status", "modified_at"]
            )

            deactivate.delay(activation.id)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        description="Restart the Activation",
        request=None,
        responses={
            status.HTTP_204_NO_CONTENT: OpenApiResponse(
                None,
                description="Activation restart was successful.",
            ),
        },
    )
    @action(methods=["post"], detail=True, rbac_action=Action.RESTART)
    def restart(self, request, pk):
        activation = get_object_or_404(models.Activation, pk=pk)
        if not activation.is_enabled:
            raise api_exc.HttpForbidden(
                detail="Activation is disabled and cannot be run."
            )

        instance_running = models.ActivationInstance.objects.filter(
            activation_id=pk, status=ActivationStatus.RUNNING
        ).first()

        if instance_running:
            deactivate_rulesets.delay(
                activation_instance_id=instance_running.id,
                deployment_type=settings.DEPLOYMENT_TYPE,
            )

        activate_rulesets.delay(
            is_restart=False,  # increment restart_count here instead of by task # noqa: E501
            activation_id=pk,
            deployment_type=settings.DEPLOYMENT_TYPE,
            ws_base_url=settings.WEBSOCKET_BASE_URL,
            ssl_verify=settings.WEBSOCKET_SSL_VERIFY,
        )

        activation.restart_count += 1
        activation.save(update_fields=["restart_count", "modified_at"])

        return Response(status=status.HTTP_204_NO_CONTENT)

    def _get_activation_dependent_objects(self, activation):
        activation["project"] = (
            models.Project.objects.get(pk=activation["project_id"])
            if activation["project_id"]
            else None
        )
        activation["decision_environment"] = (
            models.DecisionEnvironment.objects.get(
                pk=activation["decision_environment_id"]
            )
            if activation["decision_environment_id"]
            else None
        )
        activation["rulebook"] = (
            models.Rulebook.objects.get(pk=activation["rulebook_id"])
            if activation["rulebook_id"]
            else None
        )
        activation["extra_var"] = (
            models.ExtraVar.objects.get(pk=activation["extra_var_id"])
            if activation["extra_var_id"]
            else None
        )
        activation_instances = models.ActivationInstance.objects.filter(
            activation_id=activation["id"]
        )
        activation["instances"] = activation_instances
        activation["restarted_at"] = (
            activation_instances.latest("started_at").started_at
            if activation_instances
            else None
        )

        return activation

    def _get_rules_count(self, ruleset_stats):
        rules_count = 0
        rules_fired_count = 0
        for ruleset_stat in ruleset_stats.values():
            rules_count += ruleset_stat["numberOfRules"]
            rules_fired_count += ruleset_stat["rulesTriggered"]

        return rules_count, rules_fired_count


@extend_schema_view(
    retrieve=extend_schema(
        description="Get the Activation Instance by its id",
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                serializers.ActivationInstanceSerializer
            ),
        },
    ),
    list=extend_schema(
        description="List all the Activation Instances",
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                serializers.ActivationInstanceSerializer
            ),
        },
    ),
    destroy=extend_schema(
        description="Delete an existing Activation Instance",
        responses={
            status.HTTP_204_NO_CONTENT: OpenApiResponse(
                None,
                description="The Activation Instance has been deleted.",
            ),
        },
    ),
)
class ActivationInstanceViewSet(
    viewsets.ReadOnlyModelViewSet,
    mixins.DestroyModelMixin,
):
    queryset = models.ActivationInstance.objects.all()
    serializer_class = serializers.ActivationInstanceSerializer
    filter_backends = (defaultfilters.DjangoFilterBackend,)
    filterset_class = filters.ActivationInstanceFilter
    rbac_resource_type = "activation_instance"
    rbac_action = None

    @extend_schema(
        description="List all logs for the Activation Instance",
        request=None,
        responses={
            status.HTTP_200_OK: serializers.ActivationInstanceLogSerializer(
                many=True
            )
        },
        parameters=[
            OpenApiParameter(
                name="id",
                type=int,
                location=OpenApiParameter.PATH,
                description="A unique integer value identifying this Activation Instance.",  # noqa: E501
            )
        ],
    )
    @action(
        detail=False,
        queryset=models.ActivationInstanceLog.objects.order_by("id"),
        filterset_class=filters.ActivationInstanceLogFilter,
        rbac_action=Action.READ,
        url_path="(?P<id>[^/.]+)/logs",
    )
    def logs(self, request, id):
        instance_exists = models.ActivationInstance.objects.filter(
            pk=id
        ).exists()
        if not instance_exists:
            raise api_exc.NotFound(
                code=status.HTTP_404_NOT_FOUND,
                detail=f"Activation Instance with ID={id} does not exist.",
            )

        activation_instance_logs = models.ActivationInstanceLog.objects.filter(
            activation_instance_id=id
        ).order_by("id")
        activation_instance_logs = self.filter_queryset(
            activation_instance_logs
        )
        results = self.paginate_queryset(activation_instance_logs)
        serializer = serializers.ActivationInstanceLogSerializer(
            results, many=True
        )
        return self.get_paginated_response(serializer.data)
