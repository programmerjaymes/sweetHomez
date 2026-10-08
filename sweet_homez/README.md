# SweetHomez API

This Django REST API uses PostgreSQL, JWT authentication, and Django's built-in
Groups and Permissions for role-based access control.

## Setup

1. Create the PostgreSQL database (the local `.env` is already configured):

   ```sql
   CREATE DATABASE sweet_homez;
   ```

2. Install dependencies and initialize the database:

   ```bash
   ../sweethomez/bin/pip install -r requirements.txt
   ../sweethomez/bin/python manage.py migrate
   ../sweethomez/bin/python manage.py createsuperuser
   ../sweethomez/bin/python manage.py runserver
   ```

Never commit `.env`. Copy `.env.example` when configuring another environment.

## API endpoints

| Method | Endpoint | Access |
| --- | --- | --- |
| POST | `/api/auth/register/` | Public |
| POST | `/api/auth/login/` | Public |
| POST | `/api/auth/token/refresh/` | Public (refresh token required) |
| POST | `/api/auth/logout/` | Authenticated |
| GET/PATCH | `/api/auth/me/` | Authenticated |
| POST | `/api/auth/change-password/` | Authenticated |
| CRUD | `/api/users/` | Staff/admin |
| CRUD | `/api/roles/` | Staff/admin |
| GET | `/api/permissions/` | Staff/admin |
| GET | `/api/houses/` | Authenticated |
| GET | `/api/houses/{id}/` | Authenticated |
| POST/PATCH/DELETE | `/api/houses/` | Agent owner/admin |
| GET | `/api/house-media/` | Authenticated |
| POST/PATCH/DELETE | `/api/house-media/` | Agent owner/admin |
| GET | `/api/nearby-facilities/` | Authenticated |
| POST/PATCH/DELETE | `/api/nearby-facilities/` | Agent owner/admin |
| GET | `/api/house-translations/` | Authenticated |
| POST/PATCH/DELETE | `/api/house-translations/` | Agent owner/admin |
| GET | `/api/lookup-categories/` | Authenticated |
| GET | `/api/lookup-values/?category=listing_type` | Authenticated |
| GET | `/api/regions/` | Authenticated |
| GET | `/api/districts/?region={id}` | Authenticated |
| GET | `/api/wards/?district={id}` | Authenticated |
| GET | `/api/localities/?ward={id}&type=street` | Authenticated |

Every `/api/` request requires `X-API-Key: <your-api-key>`. Authenticated user
operations additionally require `Authorization: Bearer <access-token>`. Registration
intentionally cannot assign roles or staff status; an administrator assigns those
through the user and role endpoints.

Interactive Swagger documentation is available at `/docs/`; the OpenAPI schema is
available at `/api/schema/`.

House listings can be filtered with `?listing_type=rent`, `?listing_type=sale`,
`?rooms=3` (or `?bedrooms=3`), and `?region=Dar es Salaam`. Only available
houses are returned publicly. Every listing belongs to a user with the Agent role;
agent contact/profile details, media, and nearby facilities are embedded in the
house response.

Request localized content with `?lang=en`, `?lang=sw`, or the
`Accept-Language` HTTP header. Listing titles, descriptions, addresses, and
choice labels use the requested language and fall back to English.

Load or refresh the sample house listings with:

```bash
python manage.py seed_houses
```

Load or refresh geographic and property-type lookups with:

```bash
python manage.py seed_lookups
```
