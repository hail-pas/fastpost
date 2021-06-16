import pytest
from fastapi.testclient import TestClient

from tests import main_app

client = TestClient(main_app)


@pytest.mark.parametrize(
    "method, path, headers, params, body, expected_code",
    [("post", "api/user/address", {"Authorization": "Bearer askhfskjhgasoruyhgeiohgdlhgj"}, None, None, 100200,)],
)
def test_above(method, path, headers, params, body, expected_code):
    response = getattr(client, method)(path, headers=headers, params=params, json=body)
    assert response.json().get("code") == expected_code
