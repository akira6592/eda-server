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

from .activation import (
    ActivationCreateSerializer,
    ActivationInstanceLogSerializer,
    ActivationInstanceSerializer,
    ActivationListSerializer,
    ActivationReadSerializer,
    ActivationSerializer,
)
from .auth import (
    LoginSerializer,
    RoleDetailSerializer,
    RoleListSerializer,
    RoleSerializer,
)
from .credential import (
    CredentialCreateSerializer,
    CredentialRefSerializer,
    CredentialSerializer,
)
from .decision_environment import (
    DecisionEnvironmentCreateSerializer,
    DecisionEnvironmentReadSerializer,
    DecisionEnvironmentRefSerializer,
    DecisionEnvironmentSerializer,
)
from .project import (
    ExtraVarCreateSerializer,
    ExtraVarRefSerializer,
    ExtraVarSerializer,
    PlaybookSerializer,
    ProjectCreateRequestSerializer,
    ProjectReadSerializer,
    ProjectRefSerializer,
    ProjectSerializer,
    ProjectUpdateRequestSerializer,
)
from .rulebook import (
    AuditActionSerializer,
    AuditEventSerializer,
    AuditRuleDetailSerializer,
    AuditRuleListSerializer,
    AuditRuleSerializer,
    RulebookRefSerializer,
    RulebookSerializer,
    RuleOutSerializer,
    RuleSerializer,
    RulesetOutSerializer,
    RulesetSerializer,
)
from .tasks import TaskRefSerializer, TaskSerializer
from .user import (
    AwxTokenCreateSerializer,
    AwxTokenSerializer,
    CurrentUserUpdateSerializer,
    UserCreateUpdateSerializer,
    UserDetailSerializer,
    UserListSerializer,
    UserSerializer,
)

__all__ = (
    # auth
    "LoginSerializer",
    # project
    "ExtraVarSerializer",
    "ExtraVarCreateSerializer",
    "ExtraVarRefSerializer",
    "PlaybookSerializer",
    "ProjectSerializer",
    "ProjectCreateRequestSerializer",
    "ProjectUpdateRequestSerializer",
    "ProjectRefSerializer",
    "AuditActionSerializer",
    "AuditEventSerializer",
    "AuditRuleSerializer",
    "AuditRuleDetailSerializer",
    "AuditRuleListSerializer",
    "RulebookSerializer",
    "RulebookRefSerializer",
    "RulesetOutSerializer",
    "RulesetSerializer",
    "RuleOutSerializer",
    "RuleSerializer",
    # tasks
    "TaskRefSerializer",
    "TaskSerializer",
    # activations
    "ActivationSerializer",
    "ActivationListSerializer",
    "ActivationCreateSerializer",
    "ActivationReadSerializer",
    "ActivationInstanceSerializer",
    "ActivationInstanceLogSerializer",
    # users
    "AwxTokenSerializer",
    "AwxTokenCreateSerializer",
    "CurrentUserUpdateSerializer",
    "UserSerializer",
    "UserListSerializer",
    "UserCreateUpdateSerializer",
    "UserDetailSerializer",
    # credential
    "CredentialSerializer",
    "CredentialCreateSerializer",
    # decision environment
    "DecisionEnvironmentSerializer",
    # roles
    "RoleSerializer",
    "RoleListSerializer",
    "RoleDetailSerializer",
)
