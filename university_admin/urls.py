from django.urls import path
from .views import AdminLoginView, RefreshTokenView, AdminCreateView, AdminListView, AdminUpdateView, AdminDeleteView, ImportStudentsView, CandidateCreateView, CandidateListView, CandidateUpdateView, CandidateDeleteView, ElectionCreateView, ElectionListView, ElectionUpdateView, ElectionDeleteView

urlpatterns = [
    path('login/', AdminLoginView.as_view(), name='admin-login'),
    path('refresh-token/', RefreshTokenView.as_view(), name='refresh-token'),
    path('admins/create/', AdminCreateView.as_view(), name='admin-create'),
    path('admins/', AdminListView.as_view(), name='admin-list'),
    path('admins/<int:pk>/', AdminUpdateView.as_view(), name='admin-update'),
    path('admins/<int:pk>/delete/', AdminDeleteView.as_view(), name='admin-delete'),
    path('import-students/', ImportStudentsView.as_view(), name='import-students'),
    path('candidates/create/', CandidateCreateView.as_view(), name='candidate-create'),
    path('candidates/', CandidateListView.as_view(), name='candidate-list'),
    path('candidates/<int:pk>/', CandidateUpdateView.as_view(), name='candidate-update'),
    path('candidates/<int:pk>/delete/', CandidateDeleteView.as_view(), name='candidate-delete'),
    path('elections/create/', ElectionCreateView.as_view(), name='election-create'),
    path('elections/', ElectionListView.as_view(), name='election-list'),
    path('elections/<int:pk>/', ElectionUpdateView.as_view(), name='election-update'),
    path('elections/<int:pk>/delete/', ElectionDeleteView.as_view(), name='election-delete'),
]