from django.contrib import admin
from .models import Case, Invitation, Comment, PublishedAnswer, AmendedAnswer

@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'version', 'warrior', 'created_at')
    list_filter = ('status',)

@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ('case', 'doctor', 'invited_by', 'status', 'created_at')
    list_filter = ('status',)

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('case', 'author', 'is_anonymous', 'is_revealed', 'created_at')
    list_filter = ('is_anonymous', 'is_revealed')

@admin.register(PublishedAnswer)
class PublishedAnswerAdmin(admin.ModelAdmin):
    list_display = ('case', 'published_by', 'published_at')

@admin.register(AmendedAnswer)
class AmendedAnswerAdmin(admin.ModelAdmin):
    list_display = ('published_answer', 'version_number', 'amended_by', 'created_at')
