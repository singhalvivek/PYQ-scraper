from flask_smorest import Blueprint
from flask.views import MethodView
from marshmallow import Schema, fields

# Blueprint for health check endpoints
health_bp = Blueprint(
    "health",
    __name__,
    url_prefix="/api/health",
    description="Health check endpoints"
)

# -- Response schema --
class HealthResponseSchema(Schema):
    status = fields.String(required=True)
    message = fields.String(required=True)

# -- Health check endpoint --
@health_bp.route("", methods=["GET"])
class HealthCheck(MethodView):
    @health_bp.response(200, HealthResponseSchema)
    def get(self):
        """
        Health check endpoint that verifies application connectivity.
        Returns structured status information.
        """
        return {
            "status": "ok",
            "message": "Service is running"
        }
    