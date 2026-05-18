from datetime import datetime

import pytest

from . import DEFAULT_USER
from ..sync.models import Project, ProjectRole
from .utils import add_user, create_project, create_workspace
from ..sync.project_handler import ProjectHandler
from ..sync.permissions import ProjectPermissions
from ..auth.models import User

from ..app import db


def test_project_permissions(client):
    project_handler = ProjectHandler()
    project_permission = project_handler.get_push_permission(None)
    assert project_permission == ProjectPermissions.Upload


@pytest.mark.parametrize(
    "changes,expected",
    [
        (None, ProjectPermissions.Upload),
        (
            {"added": [], "updated": [], "removed": []},
            ProjectPermissions.Upload,
        ),
        (
            {"added": [{"path": "photos/photo.jpg"}], "updated": [], "removed": []},
            ProjectPermissions.Edit,
        ),
        (
            {"added": [{}], "updated": [], "removed": []},
            ProjectPermissions.Upload,
        ),
        (
            {"added": [{"path": "data/new_layer.gpkg"}], "updated": [], "removed": []},
            ProjectPermissions.Upload,
        ),
        (
            {"added": [{"path": "survey.qgs"}], "updated": [], "removed": []},
            ProjectPermissions.Upload,
        ),
        (
            {"added": [{"path": "mergin-config.json"}], "updated": [], "removed": []},
            ProjectPermissions.Upload,
        ),
        (
            {
                "added": [],
                "updated": [
                    {
                        "path": "data/base.gpkg",
                        "diff": {
                            "path": "data/base.gpkg-diff",
                            "checksum": "abc",
                            "size": 1,
                        },
                    }
                ],
                "removed": [],
            },
            ProjectPermissions.Edit,
        ),
        (
            {"added": [], "updated": [{"path": "data/base.gpkg"}], "removed": []},
            ProjectPermissions.Upload,
        ),
        (
            {"added": [], "updated": [{"path": "survey.qgz"}], "removed": []},
            ProjectPermissions.Upload,
        ),
        (
            {"added": [], "updated": [], "removed": [{"path": "photos/photo.jpg"}]},
            ProjectPermissions.Upload,
        ),
    ],
)
def test_project_push_permission_for_editor_safe_changes(changes, expected):
    assert ProjectHandler().get_push_permission(changes) == expected


def test_email_receivers(client):
    project_handler = ProjectHandler()
    # test project email receivers (owners and super admins)
    workspace = create_workspace()
    user = add_user()
    project = create_project("test_project", workspace, user)
    project.set_role(user.id, ProjectRole.READER)
    db.session.commit()
    receivers = project_handler.get_email_receivers(project)
    assert len(receivers) == 1

    project.set_role(user.id, ProjectRole.OWNER)
    db.session.commit()
    receivers = project_handler.get_email_receivers(project)
    assert len(receivers) == 2

    user.verified_email = False
    db.session.commit()
    receivers = project_handler.get_email_receivers(project)
    assert len(receivers) == 1

    user.verified_email = True
    user.profile.receive_notifications = False
    db.session.commit()
    receivers = project_handler.get_email_receivers(project)
    assert len(receivers) == 1

    user.profile.receive_notifications = True
    user.active = False
    db.session.commit()
    receivers = project_handler.get_email_receivers(project)
    assert len(receivers) == 1

    admin = User.query.filter(User.username == "mergin").first()
    admin.is_admin = False
    db.session.commit()
    receivers = project_handler.get_email_receivers(project)
    assert len(receivers) == 0


def test_get_projects_by_uuids(client):
    """Test getting projects with their UUIDs"""
    project_handler = ProjectHandler()
    test_workspace = create_workspace()
    user = User.query.filter_by(username=DEFAULT_USER[0]).first()
    p_found = create_project("p_found", test_workspace, user)
    p_removed = create_project("p_removed", test_workspace, user)
    p_removed.removed_at = datetime.now()
    db.session.commit()
    p_other = create_project("p_other", test_workspace, user)
    ids = [
        str(p_found.id),
        str(p_removed.id),
    ]

    projects = project_handler.get_projects_by_uuids(ids)
    returned_ids = [str(p.id) for p in projects]
    assert str(p_found.id) in returned_ids
    assert str(p_removed.id) not in returned_ids
    assert str(p_other.id) not in returned_ids
    assert len(projects) == 1
