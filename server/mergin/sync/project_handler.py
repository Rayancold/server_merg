import os

from .models import ProjectRole, ProjectUser, Project
from .interfaces import AbstractProjectHandler
from .permissions import ProjectPermissions
from .utils import is_qgis, is_versioned_file
from sqlalchemy import or_, and_
from typing import List
from ..auth.models import User


PROTECTED_EDITOR_FILES = {"mergin-config.json"}


class ProjectHandler(AbstractProjectHandler):
    def get_push_permission(self, changes: dict):
        """Return the minimum project permission required for a push.

        Editors may push field-data changes, but structural project changes
        still require Writer. Keep this conservative: anything unknown or
        structural falls back to Upload/Writer.
        """
        if not changes or not self._editor_safe_changes(changes):
            return ProjectPermissions.Upload
        return ProjectPermissions.Edit

    @staticmethod
    def _editor_safe_changes(changes: dict) -> bool:
        if not any(changes.get(key) for key in ("added", "updated", "removed")):
            return False

        # Removing project files is structural at server level. Feature deletes
        # are represented inside GeoPackage diffs, not as file removals.
        if changes.get("removed"):
            return False

        for item in changes.get("added", []):
            if not ProjectHandler._editor_safe_added_file(item):
                return False

        for item in changes.get("updated", []):
            if not ProjectHandler._editor_safe_updated_file(item):
                return False

        return True

    @staticmethod
    def _editor_safe_added_file(item: dict) -> bool:
        path = item.get("path", "")
        if not path:
            return False
        return not ProjectHandler._is_protected_file(path) and not is_versioned_file(
            path
        )

    @staticmethod
    def _editor_safe_updated_file(item: dict) -> bool:
        path = item.get("path", "")
        if not path:
            return False
        if ProjectHandler._is_protected_file(path):
            return False

        # Versioned data files must be updated through a geodiff changeset.
        # Full-file updates can include schema/layer changes, so they stay Writer-only.
        if is_versioned_file(path):
            return bool(item.get("diff"))

        return True

    @staticmethod
    def _is_protected_file(path: str) -> bool:
        return is_qgis(path) or os.path.basename(path) in PROTECTED_EDITOR_FILES

    def get_email_receivers(self, project: Project) -> List[User]:
        return (
            User.query.outerjoin(ProjectUser, ProjectUser.user_id == User.id)
            .filter(
                or_(
                    and_(
                        ProjectUser.project_id == project.id,
                        ProjectUser.role == ProjectRole.OWNER.value,
                    ),
                    User.is_admin,
                ),
                User.active,
                User.verified_email,
                User.receive_notifications,
            )
            .all()
        )

    @staticmethod
    def get_projects_by_uuids(uuids: List[str]) -> [Project]:
        """Gets non-deleted projects"""
        return (
            Project.query.filter(Project.id.in_(uuids))
            .filter(Project.storage_params.isnot(None))
            .filter(Project.removed_at.is_(None))
            .all()
        )
