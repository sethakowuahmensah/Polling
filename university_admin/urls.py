from django.urls import path
from .views import (
    AdminLoginView,
    RefreshTokenView,
    ImportStudentsView,
    AdminListView,
    StudentUpdateView,
    StudentDeleteView,
    StudentAddView,
    CandidateCreateView,
    CandidateListView,
    CandidateUpdateView,
    CandidateDeleteView,
    ElectionCreateView,
    ElectionListView,
    ElectionUpdateView,
    ElectionDeleteView,
    CandidateAssignPositionView,
)

urlpatterns = [
    # Authentication endpoints
    path('login/', AdminLoginView.as_view(), name='admin-login'),
    path('refresh-token/', RefreshTokenView.as_view(), name='refresh-token'),
    
    # Admin management endpoints
    path('import-students/', ImportStudentsView.as_view(), name='import-students'),
    path('list/', AdminListView.as_view(), name='admin-list'),
    path('update/<str:student_id>/', StudentUpdateView.as_view(), name='admin-update'),
    
    # Student management endpoints
    path('students/add/', StudentAddView.as_view(), name='student-add'),
    path('students/update/<str:student_id>/', StudentUpdateView.as_view(), name='student-update'),
    path('students/delete/<str:student_id>/', StudentDeleteView.as_view(), name='student-delete'),
    
    # Candidate management endpoints
    path('candidates/create/', CandidateCreateView.as_view(), name='candidate-create'),
    path('candidates/', CandidateListView.as_view(), name='candidate-list'),
    path('candidates/update/<str:student_id>/', CandidateUpdateView.as_view(), name='candidate-update'),
    path('candidates/delete/<str:student_id>/', CandidateDeleteView.as_view(), name='candidate-delete'),
    path('candidates/assign-position/<str:student_id>/', CandidateAssignPositionView.as_view(), name='candidate-assign-position'),
    
    # Election management endpoints
    path('elections/create/', ElectionCreateView.as_view(), name='election-create'),
    path('elections/', ElectionListView.as_view(), name='election-list'),
    path('elections/update/<int:pk>/', ElectionUpdateView.as_view(), name='election-update'),
    path('elections/delete/<int:pk>/', ElectionDeleteView.as_view(), name='election-delete'),
]