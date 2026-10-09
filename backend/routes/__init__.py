from flask import Flask


def register_blueprints(app: Flask) -> None:
    from routes.auth_routes import bp as auth_bp
    from routes.behavior_routes import bp as behavior_bp
    from routes.interview_routes import bp as interview_bp
    from routes.report_routes import bp as report_bp
    from routes.resume_routes import bp as resume_bp
    from routes.system_routes import bp as system_bp
    from routes.voice_routes import bp as voice_bp

    for bp in (auth_bp, interview_bp, resume_bp, voice_bp, behavior_bp, report_bp, system_bp):
        app.register_blueprint(bp)
