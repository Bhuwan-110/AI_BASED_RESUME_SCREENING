from django.contrib import admin
from .models import ResumeExtraction, ResumeScreening, ResumeAnalysis

@admin.register(ResumeExtraction)
class ResumeExtractionAdmin(admin.ModelAdmin):
    list_display = ('application', 'status', 'page_count', 'word_count', 'extracted_at')
    list_filter = ('status', 'extracted_at')
    search_fields = ('application__applicant__username', 'application__applicant__email', 'application__job__title', 'extracted_text')
    readonly_fields = ('extracted_at', 'page_count', 'word_count')

@admin.register(ResumeScreening)
class ResumeScreeningAdmin(admin.ModelAdmin):
    list_display = ('application', 'match_percentage', 'ml_predicted_class', 'ml_relevance_probability', 'status', 'screened_at')
    list_filter = ('status', 'ml_predicted_class', 'screened_at')
    search_fields = ('application__applicant__username', 'application__job__title')
    readonly_fields = ('similarity_score', 'match_percentage', 'status', 'ml_predicted_class', 'ml_relevance_probability', 'ml_confidence_tier', 'ml_model_version', 'ml_prediction_status', 'screened_at')

@admin.register(ResumeAnalysis)
class ResumeAnalysisAdmin(admin.ModelAdmin):
    list_display = ('application', 'match_percentage', 'ml_predicted_class', 'ml_relevance_probability', 'qualification_match', 'experience_match', 'analyzed_at')
    list_filter = ('qualification_match', 'experience_match', 'ml_predicted_class', 'analyzed_at')
    search_fields = ('application__applicant__username', 'application__job__title', 'explanation')
    readonly_fields = ('match_percentage', 'qualification_match', 'experience_match', 'ml_predicted_class', 'ml_relevance_probability', 'ml_confidence_tier', 'ml_model_version', 'ml_prediction_status', 'explanation', 'analyzed_at')

