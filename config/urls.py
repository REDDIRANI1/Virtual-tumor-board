from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Admin is not explicitly required in the routing for Phase 1 except /api/ auth, cases, audit,
    # but we'll include admin for completeness if needed, or just leave empty for now.
    path('admin/', admin.site.urls),
]
