from rest_framework import serializers
from .models import User , Connection


class UserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'username' , 'name', 'thumbnail'
        ]

        # join the first and lastname together
    def get_name(self,obj):
        fname = obj.first_name.capitalize()
        lname = obj.last_name.capitalize()
        return fname + ' ' + lname
    


class SignUpSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'username' , 'first_name', 'last_name' , 'password'
        ]
        extra_kwargs = {
            'password':{
                'write_only':True
            }
        }
        
    def create(self , validated_data):
        #clean all values , set as lowercase
        username = validated_data['username'].lower()
        first_name = validated_data['first_name'].lower()
        last_name = validated_data['last_name'].lower()
        #create new user
        user = User.objects.create(
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        password = validated_data['password']
        user.set_password(password)
        user.save()
        return user


class SearchSerializer(UserSerializer):
    status = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields =["username" , "name" , "thumbnail" , "status"]
        
    def get_status(self , obj):
        return 'no-connection'



class RequestSerializer(serializers.ModelSerializer):
    sender = UserSerializer()
    receiver = UserSerializer()

    class Meta:
        model = Connection
        field = [
            'id', 'sender' ,'receiver', 'created'
        ]
    
