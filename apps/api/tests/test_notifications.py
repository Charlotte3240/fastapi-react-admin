import base64
import hashlib
import hmac

import pytest
from unibiz.models.notification import NotificationTemplate
from unibiz.services import notifications


@pytest.mark.parametrize(
    "url",
    [
        "http://open.feishu.cn/open-apis/bot/v2/hook/demo",
        "https://open.feishu.cn.evil.example/open-apis/bot/v2/hook/demo",
        "https://open.feishu.cn/open-apis/bot/v2/hook/",
        "https://open.feishu.cn/open-apis/bot/v2/hook/demo?redirect=evil",
    ],
)
def test_rejects_unsafe_feishu_webhook_urls(url: str) -> None:
    with pytest.raises(ValueError):
        notifications.validate_feishu_webhook(url)


def test_channel_configuration_is_encrypted() -> None:
    webhook = "https://open.feishu.cn/open-apis/bot/v2/hook/test-token"
    encrypted = notifications.encrypt_channel_config(webhook, "signing-secret")

    assert webhook not in encrypted
    assert "signing-secret" not in encrypted
    assert notifications.decrypt_channel_config(encrypted) == {
        "webhook_url": webhook,
        "signing_secret": "signing-secret",
    }


def test_renders_text_and_post_templates() -> None:
    text_template = NotificationTemplate(
        code="customer_created",
        name="客户创建",
        message_type="text",
        title_template=None,
        body_template="客户 ${customer_name} 已创建，负责人 ${owner}",
    )
    assert notifications.render_message(
        text_template, {"customer_name": "示例公司", "owner": "小王"}
    ) == {"msg_type": "text", "content": {"text": "客户 示例公司 已创建，负责人 小王"}}

    post_template = NotificationTemplate(
        code="follow_up",
        name="跟进提醒",
        message_type="post",
        title_template="${customer_name} 跟进提醒",
        body_template="请联系 ${contact}",
    )
    result = notifications.render_message(
        post_template, {"customer_name": "示例公司", "contact": "张三"}
    )
    assert result["content"]["post"]["zh_cn"]["title"] == "示例公司 跟进提醒"
    assert result["content"]["post"]["zh_cn"]["content"][0][0]["text"] == "请联系 张三"


def test_adds_feishu_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(notifications.time, "time", lambda: 1_700_000_000)
    payload: dict = {"msg_type": "text"}

    notifications.add_signature(payload, "secret")

    expected = hmac.new(b"1700000000\nsecret", digestmod=hashlib.sha256).digest()
    assert payload["timestamp"] == "1700000000"
    assert payload["sign"] == base64.b64encode(expected).decode()
