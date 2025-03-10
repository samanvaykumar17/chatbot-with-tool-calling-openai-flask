from flask import Flask, render_template, request, session, jsonify, Response
import openai
import json
import requests
import os
import sys
from datetime import datetime

app = Flask(__name__)

if "OPENAI_API_KEY" in os.environ:
    openai.api_key = os.environ["OPENAI_API_KEY"]
else:
    sys.exit("OPENAPI_API_KEY environment variable is missing. Exiting.")

if "WEATHERAPI_KEY" in os.environ:
    weatherapi_key = os.environ["WEATHERAPI_KEY"]
else:
    sys.exit("WEATHERAPI_KEY environment variable is missing. Exiting.")


def get_completion(messages, model="gpt-3.5-turbo-1106", temperature=0, max_tokens=300, tools=None, tool_choice=None):
    response =openai.chat.completions.create (
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        tools=tools,
        tool_choice=tool_choice
    )
    return response.choices[0].message


def get_current_weather(location, unit="celsius"):
    global weatherapi_key 
    url = f"http://api.weatherapi.com/v1/current.json?key={weatherapi_key}&q={location}"
    headers = {
        "User-Agent": "Flask Weather App",
        "Accept": "application/json",
    }

    try:
        output = requests.get(url, headers).json()
        temp = output["current"]["temp_c"] if unit == "celsius" else output["current"]["temp_f"]
        return f"The temperature in {location} is {temp}°{unit[0].upper()}."
    except Exception as e:
        return "Sorry, I could not fetch the weather details."



@app.route("/")
def home():
    return render_template("hello.html", response=None)


@app.route("/ask", methods=["POST"])
def ask():
    user_input = request.form.get("query")
    conversation = session.get('conversation', []) 

    if not conversation:
        system_message = """
        Instructions: Your name is AI Bot. 
        Call get_current_weather function ONLY for weather-related queries. 
        For other queries, respond directly without using tools.
        """

        conversation = [{"role": "system", 
                         "content": system_message}]


    conversation.append({"role": "user", "content": user_input})
    session['conversation'] = conversation  

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_current_weather",
                "description": "Call this only when you need to get the current weather in a given location.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "city, state, country"},
                        "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                    },
                    "required": ["location"],
                },
            },
        }
    ]

    # Get response from OpenAI
    response = get_completion(conversation, tools=tools, tool_choice="auto")

    # Handle tool usage
    if hasattr(response, "tool_calls") and response.tool_calls:
        tool_name = response.tool_calls[0].function.name
        args = json.loads(response.tool_calls[0].function.arguments)
        if tool_name == "get_current_weather":
            response_text = get_current_weather(args["location"], args.get("unit", "celsius"))
        else:
            response_text = "Unexpected tool was called."
    else:
        # Default assistant response for non-tool queries
        response_text = response.content.strip()

    # Add assistant's response to conversation
    conversation.append({"role": "assistant", "content": response_text})
    session['conversation'] = conversation  # Save updated conversation to session

    user_conversation = conversation[1:]

    return render_template("hello.html", conversation=user_conversation)

if __name__ == "__main__":
    app.secret_key = os.urandom(24)
    app.run(port=3001)

