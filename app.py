import os
from flask import Flask, render_template, request
from dotenv import load_dotenv
from anthropic import Anthropic
import markdown

load_dotenv()

app = Flask(__name__)

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


@app.route("/", methods=["GET", "POST"])
def home():
    ai_response = None

    if request.method == "POST":
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
                    """

                }
            ]
        )

        ai_response = markdown.markdown(message.content[0].text)

    return render_template("index.html", ai_response=ai_response)


if __name__ == "__main__":
    app.run(debug=True, port=5004)
