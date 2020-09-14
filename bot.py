import os
import json
import urllib.parse

from flask import Flask, request, render_template, abort

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError,
    LineBotApiError,
)
from linebot.models import *

app = Flask(__name__)

# 環境変数読み込み
line_channel_access_token = os.environ['LINE_CHANNEL_ACCESS_TOKEN']
line_channel_secret = os.environ['LINE_CHANNEL_SECRET']
debug = os.environ.get('DEBUG', 'False') == 'True'
liff_ids = {
    "full": os.environ['LIFF_ID_FULL'],
    "tall": os.environ['LIFF_ID_TALL'],
    "compact": os.environ['LIFF_ID_COMPACT'],
}

line_bot_api = LineBotApi(line_channel_access_token)
handler = WebhookHandler(line_channel_secret)


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


def template_render(liff_type, title):
    liff_id = liff_ids[liff_type]

    param = {
        "liff_id": liff_id,
        "title": urllib.parse.unquote(title),
        "debug": debug,
    }
    return render_template("liff_page.html", **param)


def show_liff(liff_type, page="None"):
    if request.args.get("liff.state"):
        # 1次リダイレクト
        return template_render(liff_type, "login")

    # 2次リダイレクト
    return template_render(liff_type, page)


@app.route("/liff/<liff_type>", methods=['GET'])
def show_liff_1st(liff_type):
    return show_liff(liff_type)


@app.route("/liff/<liff_type>/<page>", methods=['GET'])
def show_liff_2nd(liff_type, page):
    return show_liff(liff_type, page)


def is_connection_check(event):
    check_uid = 'Udeadbeefdeadbeefdeadbeefdeadbeef'
    check_tokens = [
        '00000000000000000000000000000000',
        'ffffffffffffffffffffffffffffffff',
    ]
    if event.source.type == 'user':
        if event.source.user_id == check_uid:
            return True
    if event.reply_token in check_tokens:
        return True
    return False


@handler.default()
def default(event):
    if is_connection_check(event):
        return

    event_text = json.dumps(event.as_json_dict())

    if debug:
        print(event_text)

    reply_msgs = []
    reply_msgs.append(TextSendMessage(text="イベント内容"))
    reply_msgs.append(TextSendMessage(text=event_text))

    try:
        line_bot_api.reply_message(event.reply_token, reply_msgs)
    except:
        pass


@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    if is_connection_check(event):
        return

    text = event.message.text

    contents = [TextComponent(text=text, weight="bold", size="xl")]
    contents.extend([ButtonComponent(action=URIAction(
        label=k, uri=f"https://liff.line.me/{v}/{urllib.parse.quote(text)}")) for k, v in liff_ids.items()])

    reply_msgs = []
    reply_msgs.append(FlexSendMessage(alt_text=text, contents=BubbleContainer(
        body=BoxComponent(layout="vertical", contents=contents))))
    line_bot_api.reply_message(event.reply_token, reply_msgs)


if __name__ == "__main__":
    app.run(debug=debug)
