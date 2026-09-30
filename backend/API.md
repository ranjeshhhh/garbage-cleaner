# REST API reference

Base URL: `http://localhost:8000/api`. JSON endpoints accept and return JSON; authenticated endpoints require `Authorization: Bearer <JWT>`. Interactive OpenAPI documentation is served at `/docs`.

`GET /api/health` is a public health check intended for hosting providers.

| Method | Path | Access | Purpose |
|---|---|---|---|
| POST | `/auth/register` | Public | Create customer, collector, or recycler account |
| POST | `/auth/login` | Public | Authenticate and return bearer token |
| GET / PUT | `/users/me` | Signed in | Read/update basic profile fields |
| GET | `/waste-categories` | Public | Current material catalogue and rates |
| POST | `/pickup-requests` | Customer | Create a pickup (address, optional coordinates, category, quantity, image URLs) |
| GET | `/pickup-requests` | Signed in | Role-filtered pickup list; supports `status` and `category` query filters |
| GET | `/pickup-requests/{id}` | Customer, assigned collector, admin | Read authorized pickup detail |
| POST | `/pickup-requests/{id}/accept` | Verified collector | Accept an open request |
| PUT | `/pickup-requests/{id}/status` | Customer (cancel), assigned collector, admin | Update an allowed pickup state |
| POST | `/pickup-requests/{id}/collection` | Assigned collector | Record actual weight; calculates value and creates a batch |
| GET | `/collector/summary` | Collector | Collection counts and recorded value |
| GET | `/materials` | Signed in | List collector inventory or recycler material marketplace/inventory |
| POST | `/materials/{id}/accept` | Verified recycler | Receive an available batch |
| PUT | `/materials/{id}/status` | Assigned recycler | Advance batch to Processing or Recycled |
| GET | `/notifications` | Signed in | Read current user's notifications |
| PUT | `/notifications/{id}/read` | Owner | Mark a notification read |
| POST | `/uploads` | Signed in | Upload up to five JPEG/PNG/WebP files, 5 MB each |
| POST | `/complaints` | Signed in | Create a support request |
| GET | `/impact` | Signed in | Calculated completed collection/recycling figures |
| GET | `/admin/dashboard` | Admin | Platform counts and material totals |
| GET | `/admin/users` | Admin | Searchable client-side account list |
| PUT | `/admin/users/{id}/verification` | Admin | Verify/decline collector or recycler |
| PUT | `/admin/users/{id}/status` | Admin | Suspend/restore account |
| PUT | `/admin/categories/{id}/price` | Admin | Change current rate per unit |
| GET | `/admin/complaints` | Admin | List member support requests |
| PUT | `/admin/complaints/{id}` | Admin | Advance support request to In Review or Resolved |

Pickup states currently supported in the app: Finding Collector → Accepted → On The Way → Arrived → Completed (on weight submission), plus cancellation by customer. The collection endpoint persists actual weight, price, and material batch in one database transaction boundary at the request level. Payment collection is not integrated.
