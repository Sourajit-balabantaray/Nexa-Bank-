"""Authenticated notification inbox routes."""

from flask import Blueprint, abort, redirect, render_template, url_for
from flask_login import current_user, login_required

from extensions import db
from models.notification import Notification

notifications_bp = Blueprint('notifications', __name__, url_prefix='/notifications')


@notifications_bp.route('/', strict_slashes=False)
@login_required
def index():
    notifications = current_user.notifications.order_by(
        Notification.created_at.desc()
    ).all()
    return render_template('notifications.html', notifications=notifications)


@notifications_bp.route('/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_read(notification_id):
    notification = current_user.notifications.filter_by(id=notification_id).first()
    if notification is None:
        abort(404)

    notification.is_read = True
    db.session.commit()
    return redirect(url_for('notifications.index'))


@notifications_bp.route('/read-all', methods=['POST'])
@login_required
def mark_all_read():
    current_user.notifications.filter_by(is_read=False).update(
        {Notification.is_read: True},
        synchronize_session='fetch'
    )
    db.session.commit()
    return redirect(url_for('notifications.index'))
