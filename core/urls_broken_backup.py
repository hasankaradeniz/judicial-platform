from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views
from . import ai_views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('search-results/', views.combined_search_results, name='combined_search_results'),
    path('judicial-decisions/', views.judicial_decisions, name='judicial_decisions'),
    path('articles/', views.articles, name='articles'),
    path('article/search_results/', views.article_search_results, name='article_search_results'),
    path('article/<int:pk>/', views.article_detail, name='article_detail'),
    path('paketler/', views.paketler, name='paketler'),
    path('profile/', views.profile, name='profile'),
    path('gizlilik-politikasi/', views.gizlilik_politikasi, name='gizlilik_politikasi'),
    path('kullanici-sozlesmesi/', views.kullanici_sozlesmesi, name='kullanici_sozlesmesi'),
    path('mesafeli-satis-sozlesmesi/', views.mesafeli_satis_sozlesmesi, name='mesafeli_satis_sozlesmesi'),
    path('teslimat-iade-sartlari/', views.teslimat_iade_sartlari, name='teslimat_iade_sartlari'),
    path('search/', views.search_results, name='search_results'),
    path('judicial/<int:pk>/', views.judicial_detail, name='judicial_detail'),
    path('api/search/', views.api_search, name='api_search'),
    path('subscription/payment/<str:package>/', views.subscription_payment, name='subscription_payment'),
    path('subscription/success/', views.subscription_success, name='subscription_success'),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('payment/fail/', views.payment_fail, name='payment_fail'),
    path('3d-sonuc/', views.payment_3d_callback, name='payment_3d_callback'),
    path('demo-payment/', views.demo_payment, name='demo_payment'),
    path('protected/', views.some_protected_view, name='protected'),
    path('ai-features/', views.ai_features_home, name='ai_features_home'),
#     path('legislation/', views.legislation_home, name='legislation_home'),
    path('ziyaretci-veri-koruma/', views.ziyaretci_veri_koruma, name='ziyaretci_veri_koruma'),
    # AI URLs - proper AI views
    path('ai/assistant/home/', ai_views.ai_assistant_home, name='ai_assistant_home'),
    path('ai/assistant/', ai_views.ai_assistant_api, name='ai_assistant_api'),
    path('ai/case-analyzer/', ai_views.contract_risk_analyzer, name='contract_risk_analyzer'),
    path('ai/analyze-contract/', ai_views.analyze_contract, name='analyze_contract'),
    path('ai/text-generator/', ai_views.legal_text_generator_home, name='legal_text_generator_home'),
    path('ai/generate-text/', ai_views.generate_legal_text, name='generate_legal_text'),
    path('ai/generate-from-multiple-documents/', ai_views.generate_from_multiple_documents, name='generate_from_multiple_documents'),
    path('ai/get-template-fields/', ai_views.get_template_fields, name='get_template_fields'),
    path('ai/save-text/', ai_views.save_generated_text, name='save_generated_text'),
    # Profile URL (both for /profile/ and /accounts/profile/)
    path('accounts/profile/', views.profile, name='account_profile'),
    path('signup/', views.signup, name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    # Password reset URLs
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='core/password_reset.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='core/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='core/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='core/password_reset_complete.html'), name='password_reset_complete'),
    # Faiss query app
    path('faiss/', include('faiss_query.urls')),
    path("article/pdf/<str:source>/<str:article_id>/", views.article_pdf_viewer, name="article_pdf_viewer"),
    path("article/proxy-pdf/", views.proxy_pdf, name="proxy_pdf"),
    path("test-pdf-display/", views.test_pdf_display, name="test_pdf_display"),
    path("debug-pdf-test/", views.debug_pdf_test, name="debug_pdf_test"),
]