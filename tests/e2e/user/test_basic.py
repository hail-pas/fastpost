import pytest
from fastapi.testclient import TestClient

from fastpost.factory import current_app

client = TestClient(current_app)


@pytest.mark.parametrize(
    "method, path, headers, params, body, expected_code",
    [
        (
            "post",
            "api/user/address",
            {
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxfQ.v1zQUnB4-WXrjFV6MbsKxv6JFm7_KrLbll695qEPcTg"  # noqa: E501
            },
            None,
            None,
            100200,
        )
    ],
)
def test_above(method, path, headers, params, body, expected_code):
    response = getattr(client, method)(path, headers=headers, params=params, json=body)
    assert response.json().get("code") == expected_code
