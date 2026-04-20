import pytest
import allure
from apitf.http_client import HttpClient
from apitf.validators.jsonplaceholder_validator import (
    JsonplaceholderValidator,
    CommentValidator,
    UserValidator,
    TodoValidator,
    AlbumValidator,
)
pytestmark = [pytest.mark.jsonplaceholder, allure.suite("jsonplaceholder")]


@allure.title("TC-001: GET /posts/{id} positive — valid id returns 200 and schema-valid body")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_post_by_id_positive(env_config: dict) -> None:
    cfg = env_config["jsonplaceholder"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/posts/1")
    assert resp.status_code == 200
    result = JsonplaceholderValidator().validate(resp.json_body)
    assert result.passed, result.errors


@allure.title("TC-002: GET /posts positive — list returns 200 and first item is schema-valid")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_posts_list_positive(env_config: dict) -> None:
    cfg = env_config["jsonplaceholder"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/posts")
    assert resp.status_code == 200
    assert isinstance(resp.json_body, list)
    result = JsonplaceholderValidator().validate(resp.json_body[0])
    assert result.passed, result.errors


@allure.title("TC-003: GET /posts/{id}/comments positive — returns 200 and first comment is schema-valid")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_post_comments_positive(env_config: dict) -> None:
    cfg = env_config["jsonplaceholder"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/posts/1/comments")
    assert resp.status_code == 200
    assert isinstance(resp.json_body, list)
    result = CommentValidator().validate(resp.json_body[0])
    assert result.passed, result.errors


@allure.title("TC-004: GET /users/{id} positive — returns 200 and schema-valid body")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_user_by_id_positive(env_config: dict) -> None:
    cfg = env_config["jsonplaceholder"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/users/1")
    assert resp.status_code == 200
    result = UserValidator().validate(resp.json_body)
    assert result.passed, result.errors


@allure.title("TC-005: GET /todos/{id} positive — returns 200 and schema-valid body")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_todo_by_id_positive(env_config: dict) -> None:
    cfg = env_config["jsonplaceholder"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/todos/1")
    assert resp.status_code == 200
    result = TodoValidator().validate(resp.json_body)
    assert result.passed, result.errors


@allure.title("TC-006: GET /albums/{id} positive — returns 200 and schema-valid body")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_album_by_id_positive(env_config: dict) -> None:
    cfg = env_config["jsonplaceholder"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/albums/1")
    assert resp.status_code == 200
    result = AlbumValidator().validate(resp.json_body)
    assert result.passed, result.errors


@allure.title("TC-007: GET /posts/{id} equivalence partitioning — mid-range valid id returns 200")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_post_mid_range_equivalence(env_config: dict) -> None:
    cfg = env_config["jsonplaceholder"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/posts/50")
    assert resp.status_code == 200
    assert resp.json_body["id"] == 50


@allure.title("TC-008: GET /users/{id} equivalence partitioning — mid-range valid id returns 200")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_user_mid_range_equivalence(env_config: dict) -> None:
    cfg = env_config["jsonplaceholder"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/users/5")
    assert resp.status_code == 200
    assert resp.json_body["id"] == 5


@allure.title("TC-009: GET /posts/1 boundary — minimum valid id returns id field equal to 1")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_post_minimum_id_boundary(env_config: dict) -> None:
    cfg = env_config["jsonplaceholder"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/posts/1")
    assert resp.status_code == 200
    assert resp.json_body["id"] == 1


@allure.title("TC-010: GET /posts/9999 boundary — out-of-range id returns 404")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_post_out_of_range_boundary(env_config: dict) -> None:
    cfg = env_config["jsonplaceholder"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/posts/9999")
    assert resp.status_code == 404


@allure.title("TC-011: GET /users/1 boundary — minimum valid id returns id field equal to 1")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_user_minimum_id_boundary(env_config: dict) -> None:
    cfg = env_config["jsonplaceholder"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/users/1")
    assert resp.status_code == 200
    assert resp.json_body["id"] == 1


@allure.title("TC-012: GET /posts/0 negative — zero id returns 404")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_post_zero_id_negative(env_config: dict) -> None:
    cfg = env_config["jsonplaceholder"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/posts/0")
    assert resp.status_code == 404


@allure.title("TC-013: GET /users/9999 negative — out-of-range id returns 404")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_user_not_found_negative(env_config: dict) -> None:
    cfg = env_config["jsonplaceholder"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/users/9999")
    assert resp.status_code == 404


@allure.title("TC-014: GET /todos/9999 negative — out-of-range id returns 404")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_todo_not_found_negative(env_config: dict) -> None:
    cfg = env_config["jsonplaceholder"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/todos/9999")
    assert resp.status_code == 404


@allure.title("TC-015: GET /albums/9999 negative — out-of-range id returns 404")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_album_not_found_negative(env_config: dict) -> None:
    cfg = env_config["jsonplaceholder"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/albums/9999")
    assert resp.status_code == 404


@allure.title("TC-016: GET /posts performance — response time within SLA threshold")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_posts_list_performance(env_config: dict) -> None:
    cfg = env_config["jsonplaceholder"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/posts")
    assert resp.response_time_ms < cfg["thresholds"]["max_response_time"] * 1000


@allure.title("TC-017: GET /posts/{id} performance — response time within SLA threshold")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_post_by_id_performance(env_config: dict) -> None:
    cfg = env_config["jsonplaceholder"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/posts/1")
    assert resp.response_time_ms < cfg["thresholds"]["max_response_time"] * 1000


@allure.title("TC-018: GET /users/{id} performance — response time within SLA threshold")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_user_by_id_performance(env_config: dict) -> None:
    cfg = env_config["jsonplaceholder"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/users/1")
    assert resp.response_time_ms < cfg["thresholds"]["max_response_time"] * 1000


@allure.title("TC-019: GET /todos/{id} performance — response time within SLA threshold")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_todo_by_id_performance(env_config: dict) -> None:
    cfg = env_config["jsonplaceholder"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/todos/1")
    assert resp.response_time_ms < cfg["thresholds"]["max_response_time"] * 1000


@allure.title("TC-020: Security — HttpClient rejects plain HTTP base URL with ValueError")
def test_https_enforcement_security(env_config: dict) -> None:
    cfg = env_config["jsonplaceholder"]
    with pytest.raises(ValueError, match="HTTPS"):
        HttpClient(cfg["base_url"].replace("https://", "http://"))


@allure.title("TC-021: GET /posts/1 state — body contains all required fields with correct types")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_post_state_required_fields(env_config: dict) -> None:
    cfg = env_config["jsonplaceholder"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/posts/1")
    assert resp.status_code == 200
    body = resp.json_body
    assert isinstance(body["id"], int)
    assert isinstance(body["userId"], int)
    assert isinstance(body["title"], str)
    assert isinstance(body["body"], str)
    assert len(body["title"]) > 0
    assert len(body["body"]) > 0


@allure.title("TC-022: GET /posts/1/comments state — every comment has postId equal to 1")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_post_comments_state_postid_consistency(env_config: dict) -> None:
    cfg = env_config["jsonplaceholder"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/posts/1/comments")
    assert resp.status_code == 200
    for comment in resp.json_body:
        assert comment["postId"] == 1


@allure.title("TC-023: GET /users/1 state — body contains all required fields with correct types")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_user_state_required_fields(env_config: dict) -> None:
    cfg = env_config["jsonplaceholder"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/users/1")
    assert resp.status_code == 200
    body = resp.json_body
    assert isinstance(body["id"], int)
    assert isinstance(body["name"], str)
    assert isinstance(body["username"], str)
    assert isinstance(body["email"], str)
    assert isinstance(body["phone"], str)
    assert isinstance(body["website"], str)


@allure.title("TC-024: GET /todos/1 state — completed field is boolean and title is non-empty string")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_todo_state_fields(env_config: dict) -> None:
    cfg = env_config["jsonplaceholder"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/todos/1")
    assert resp.status_code == 200
    body = resp.json_body
    assert isinstance(body["completed"], bool)
    assert isinstance(body["title"], str)
    assert len(body["title"]) > 0


@allure.title("TC-025: GET /posts state — list contains 100 items each with required fields")
@pytest.mark.flaky(reruns=2, reruns_delay=2)
def test_get_posts_list_state_count_and_fields(env_config: dict) -> None:
    cfg = env_config["jsonplaceholder"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/posts")
    assert resp.status_code == 200
    posts = resp.json_body
    assert len(posts) == 100
    for post in posts:
        assert "id" in post
        assert "userId" in post
        assert "title" in post
        assert "body" in post


@allure.title("TC-026: GET /posts/9999/comments xfail — JSONPlaceholder returns 200+empty not 404")
@pytest.mark.xfail(
    strict=False,
    raises=AssertionError,
    reason=(
        "JSONPlaceholder by design returns 200 with empty list for non-existent post comments "
        "instead of 404. Known platform behavior, not a spec violation requiring a filed bug."
    ),
)
def test_get_comments_nonexistent_post_xfail(env_config: dict) -> None:
    cfg = env_config["jsonplaceholder"]
    with HttpClient(cfg["base_url"]) as client:
        resp = client.get("/posts/9999/comments")
    assert resp.status_code == 404