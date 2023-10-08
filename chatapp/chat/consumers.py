from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
import json
from django.core.files.base import ContentFile
import base64
from .serializers import UserSerializer


class ChatConsumer(WebsocketConsumer):

    def conect(self):
        user = self.scope['user']
        print(user , user.is_authenticated)
        if not user.is_authenticated:
            return
        # save username to use a group name for this user
        self.username = user.username
        # join this user to a group with their username

        async_to_sync(self.channel_layer.group_add)(
            self.username , self.channel_name
        )
        self.accept()


    def disconnect(self , close_code) :
        # Leave room/group
        async_to_sync(self.channel_layer.group_discard)(
            self.username , self.channel_name
        )

    #----------------------
    # Handle Requests
    #-----------

    def receive(self , text_data):
        # Receive message from websocket
        data = json.load(text_data)
        data_source = data.get('source')

        #print py dictionary
        print('receive ', json.dumps(data , indent=2))

        #Thumbnail upload
        if data_source == 'thumbnail':
            self.receiver_thumbnail(data)


    def receive_thumbnail(self , data):
        user = self.scope['user']
        # convert base64 data to a django content file
        image_str = data.get('base64')
        image = ContentFile(base64.b64decode(image_str))

        #update thumbnail field

        filename = data.get('filename')
        user.thumbnail.save(filename , image , save=True)
        #serialize user
        serialized = UserSerializer(user)
        #send updated user data including new thumbnail
        self.send_group(self.username, 'thumbnail',serialized.data )

    #---------------------------
    # catch/all broadcast to client helpers
    #--------------------

    def send_group(self , group , source , data):
        response = {
            'type':'broadcast_group',
            'source':source,
            'data': data
        }
        async_to_sync(self.channel_layer.group_send)(
            group, response
        )

    def broadcast_group(self , data):
        '''
        data:
        -type:'broadcast_group'
        -source:where it originated from
        -data:what ever you want to send as a dict
        '''
        data.pop('type')
        '''
        return data:
        -type:'broadcast_group'
        -source:where it originated from
        -data:what ever you want to send as a dict
        '''
    
        
    
        self.send(text_data = json.dumps(data))


