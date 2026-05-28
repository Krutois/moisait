import click
from flask.cli import with_appcontext

from extensions import bcrypt, db
from models import User


@click.command("create-admin")
@click.option("--username", prompt=True, default="admin", show_default=True)
@click.option("--email", prompt=True)
@click.password_option("--password", confirmation_prompt=True)
@with_appcontext
def create_admin(username, email, password):
    """Create or promote a SmartLecture administrator."""
    username = username.strip()
    email = email.strip().lower()

    if len(password) < 8:
        raise click.ClickException("Password must contain at least 8 characters.")

    user = User.query.filter_by(email=email).first()
    if user:
        user.role = "admin"
        click.echo(f"Existing user {email} promoted to admin.")
    else:
        if User.query.filter_by(username=username).first():
            raise click.ClickException("Username already exists.")
        user = User(
            username=username,
            email=email,
            role="admin",
            password_hash=bcrypt.generate_password_hash(password).decode("utf-8"),
        )
        db.session.add(user)
        click.echo(f"Admin {email} created.")

    db.session.commit()


def init_app(app):
    app.cli.add_command(create_admin)
