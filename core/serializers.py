# core/serializers.py
from rest_framework import serializers
from .models import JudicialDecision, Article

class JudicialDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = JudicialDecision
        fields = '__all__'

class ArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = '__all__'
