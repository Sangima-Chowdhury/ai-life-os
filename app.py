import json
import os
from flask import Flask, render_template, request, send_file
from dotenv import load_dotenv
from anthropic import Anthropic
import markdown
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO

load_dotenv()

app = Flask(__name__)

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def load_plans():
    try:
        with open("plans.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return []


def save_plan(category, problem, plan):
    plans = load_plans()

    new_plan = {
        "category": category,
        "problem": problem,
        "plan": plan
    }

    plans.append(new_plan)

    with open("plans.json", "w") as file:
        json.dump(plans, file, indent=4)


@app.route("/", methods=["GET", "POST"])
def home():
    ai_response = None

    if request.method == "POST":
        category = request.form.get("category")
        user_problem = request.form.get("problem")

        message = client.messages.create(
            model="claude-haiku-4-5",
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
        save_plan(category, user_problem, ai_response)

    saved_plans = load_plans()

    return render_template(
        "index.html",
        ai_response=ai_response,
        saved_plans=saved_plans
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


if __name__ == "__main__":
    app.run(debug=True, port=5004)
