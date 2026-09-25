import pytest
from unittest.mock import Mock
from aniworld.search import random_anime
from aniworld import search
import random

@pytest.fixture
def mock_session_post(monkeypatch):
    """Fixture to mock GLOBAL_SESSION.post"""
    mock_post = Mock()
    monkeypatch.setattr(search.GLOBAL_SESSION, "post", mock_post)
    return mock_post

@pytest.fixture
def mock_random_choice(monkeypatch):
    """Fixture to mock random.choice to always return the first item."""
    monkeypatch.setattr(random, "choice", lambda seq: seq[0])

def test_random_anime_success(mock_session_post, mock_random_choice):
    """Test that random_anime correctly fetches and returns a URL."""
    # Setup mock response
    mock_response = Mock()
    mock_response.json.return_value = [{"link": "bullbuster"}, {"link": "one-piece"}]
    mock_response.raise_for_status = Mock()
    mock_session_post.return_value = mock_response

    result = random_anime()

    assert result == "https://aniworld.to/anime/stream/bullbuster"
    mock_session_post.assert_called_once_with(
        search.RANDOM_URL,
        data={"productionStart": "all", "productionEnd": "all", "genres[]": "all"}
    )
    mock_response.raise_for_status.assert_called_once()

def test_random_anime_empty_result(mock_session_post):
    """Test when the API returns an empty list."""
    mock_response = Mock()
    mock_response.json.return_value = []
    mock_response.raise_for_status = Mock()
    mock_session_post.return_value = mock_response

    result = random_anime()

    assert result is None
    mock_session_post.assert_called_once()

def test_random_anime_missing_link(mock_session_post, mock_random_choice):
    """Test when the randomly chosen series is missing a link."""
    mock_response = Mock()
    mock_response.json.return_value = [{"title": "no-link-anime"}]
    mock_response.raise_for_status = Mock()
    mock_session_post.return_value = mock_response

    result = random_anime()

    assert result is None
    mock_session_post.assert_called_once()

def test_random_anime_http_error(mock_session_post):
    """Test when the HTTP request fails."""
    mock_session_post.side_effect = Exception("HTTP Error")

    result = random_anime()

    assert result is None
    mock_session_post.assert_called_once()
