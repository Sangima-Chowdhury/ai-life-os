from email.mime import message

from models import db, User, Plan
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os
from flask import Flask, render_template, request, send_file, session, redirect, url_for
from dotenv import load_dotenv
from anthropic import Anthropic
import markdown
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///ai_life_os.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()


client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def load_plans():
    try:
        with open("plans.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return []


def save_plan(username, category, problem, plan):
    new_plan = Plan(
        username=username,
        category=category,
        problem=problem,
        plan=plan
    )

    db.session.add(new_plan)
    db.session.commit()


def load_users():
    try:
        with open("users.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return []


def save_users(users):
    with open("users.json", "w") as file:
        json.dump(users, file, indent=4)


@app.route("/", methods=["GET", "POST"])
def home():
    ai_response = None
    username = session.get("username")
    saved_plans = []
    if not username:
        return redirect(url_for("login"))

    if request.method == "POST":
        category = request.form.get("category")
        user_problem = request.form.get("problem")

        try:
            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1000,
                messages=[
                    {
                        "role": "user",
                        "content": f"""
                        You are an AI Life OS assistant.

                    the user will share a life, career, study, productivity or personal problem.

                    Give a practical structured action plan to solve the problem.

                    Use this format:

                    1. Situation Summary: A brief summary of the problem.
                    2. Main Problem: The core issue that needs to be addressed.
                    3. Practical Next Steps: A list of actionable steps the user can take to address the problem.
                    4. Resources: Any resources (books, websites, tools) that could help the user.
                    5. 7-Day Action Plan: A day-by-day breakdown of actions the user can take over the next week to start addressing the problem.
                    6. Final note of Encouragement: A motivational message to encourage the user to take action. Give some additional tips too.

                    User Problem: {user_problem}
                    Category: {category}
                    """
                    }
                ]
            )

            ai_response = markdown.markdown(message.content[0].text)

            save_plan(
                username,
                category,
                user_problem,
                ai_response
            )

        except Exception as e:
            return f"Claude Error: {str(e)}"

    if username:
        saved_plans = Plan.query.filter_by(username=username).all()

    return render_template(
        "index.html",
        ai_response=ai_response,
        saved_plans=saved_plans,
        username=username
    )


@app.route("/download-pdf", methods=["POST"])
def download_pdf():
    plan_text = request.form.get("plan_text")

    buffer = BytesIO()

    pdf = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("AI Life OS Action Plan", styles['Title']))
    story.append(Spacer(1, 12))

    for line in plan_text.split("\n"):
        if line.strip():
            story.append(Paragraph(line, styles["BodyText"]))
            story.append(Spacer(1, 6))

    pdf.build(story)

    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name="ai_life_os_action_plan.pdf",
        mimetype="application/pdf"
    )


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        existing_user = User.query.filter_by(username=username).first()

        if existing_user:
            return "Username already exists. Please choose a different one."

        hashed_password = generate_password_hash(password)

        new_user = User(username=username, password=hashed_password)

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for("home"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session["username"] = username
            return redirect(url_for("home"))

        return "Invalid username or password. Please try again."

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/delete-plan/<int:plan_id>", methods=["POST"])
def delete_plan(plan_id):
    username = session.get("username")

    plan = Plan.query.filter_by(
        id=plan_id,
        username=username
    ).first()
    if plan:
        db.session.delete(plan)
        db.session.commit()

    return redirect(url_for("home"))


@app.route("/plan/<int:plan_id>")
def view_plan(plan_id):
    username = session.get("username")

    plan = Plan.query.filter_by(
        id=plan_id,
        username=username
    ).first()

    if not plan:
        return "Plan not found."

    return render_template("plan.html", plan=plan)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True, port=5004)
