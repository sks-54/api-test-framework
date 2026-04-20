# JSONPlaceholder API Spec

JSONPlaceholder is a free online REST API for testing and prototyping.
All resources are read-only. No authentication required.

Base URL: https://jsonplaceholder.typicode.com

## Overview

The API provides six resources: posts, comments, albums, photos, todos, and users.
All endpoints return JSON. The API supports GET, POST, PUT, PATCH, and DELETE methods
but this spec focuses on the GET endpoints used for validation testing.

## Endpoints

| Method | Path | Response Fields |
|--------|------|----------------|
| GET | /posts/{id} | id, userId, title, body |
| GET | /posts | id, userId, title, body |
| GET | /posts/{id}/comments | id, postId, name, email, body |
| GET | /users/{id} | id, name, username, email, phone, website |
| GET | /todos/{id} | id, userId, title, completed |
| GET | /albums/{id} | id, userId, title |

## Response Field Contracts

### POST `/posts/{id}`
Returns a single post object.
- `id` — integer, unique post identifier
- `userId` — integer, foreign key to users
- `title` — non-empty string
- `body` — non-empty string

### GET `/users/{id}`
Returns a single user object.
- `id` — integer, unique user identifier
- `name` — full name string
- `username` — login handle string
- `email` — valid email address string
- `phone` — phone number string
- `website` — website URL string

### GET `/todos/{id}`
Returns a single todo object.
- `id` — integer, unique todo identifier
- `userId` — integer, foreign key to users
- `title` — non-empty string
- `completed` — boolean

## SLA

All endpoints must respond within 3 seconds.

## Negative Paths

- `GET /posts/999999` — returns 404 for a nonexistent post ID
- `GET /users/999999` — returns 404 for a nonexistent user ID
- `GET /todos/999999` — returns 404 for a nonexistent todo ID
