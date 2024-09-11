from django.contrib.auth.models import User

from rest_framework import serializers

from .models import Note, Category

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'password', 'email']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            email=validated_data.get('email')
        )
        return user

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

class NoteSerializer(serializers.ModelSerializer):
    category = CategorySerializer()

    class Meta:
        model = Note
        fields = ['id', 'title', 'content', 'created_at', 'category']

    def create(self, validated_data):
        category_data = validated_data.pop('category')
        category = Category.objects.get_or_create(name=category_data['name'])
        note = Note.objects.create(category=category, **validated_data)
        return note