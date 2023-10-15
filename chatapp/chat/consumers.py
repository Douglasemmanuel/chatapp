# from channels.generic.websocket import WebsocketConsumer
from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
import json
from django.core.files.base import ContentFile
import base64
from .serializers import UserSerializer , SearchSerializer , RequestSerializer , MessageSerializer , FriendSerializer
from .models import User , Connection , Message
from django.db.models import Q,  Exists, OuterRef
from django.db.models.functions import Coalesce


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


        # Accept Friend request
        if data_source == 'request.accept':
            self.receive_request_accept(data)
        
        # Get Friend request
        elif data_source == 'request.list':
            self.receive_request_friend_list(data)
        
        #search / Filter users
        elif data_source == 'search':
            self.receive_search(data)
       
        # Make Friend request
        elif data_source == 'request.connect':
            self.receive_request_connect(data)
        
        # Get  request List
        elif data_source == 'request.list':
            self.receive_request_list(data)
       
        # Message List
        elif data_source == 'message.list':
            self.receive_message_list(data)
        
        # message has not been sent
        elif data_source == 'message.send':
            self.receive_message_send(data)

        # User is typing message
        elif data_source == 'message.type':
            self.receive_message_type(data)

        #Thumbnail upload
        elif data_source == 'thumbnail':
            self.receiver_thumbnail(data)


  # to enable a useer connect with another user
    def receive_request_connect(self , data):
        username = data.get('username')
        #attempt to fetch the receiving user
        try:
            receiver = User.objects.get(username=username)
        except User.DoesNotExist:
            print('Error User not Found')
            return 
        # create connection
        connection = Connection.objects.get_or_create(
            sender=self.scope['user'],
            receiver=receiver
        )
        # serialized connection
        serialized = RequestSerializer(connection )

        # send back to sender
        self.send_group(connection.sender.username , 'request.connect' , serialized.data)
        # send to the receiver
        self.send_group(
            connection.receiver.username , 'request.connect' , serialized.data
        )
        

# function to enable the user receive for friends request
    def receive_request_list(self, data):
        user = self.scope['user']
        # Get connection made to this user
        connection = Connection.objects.filter(
            receiver=user,
            accepted=False
        )
        serialized = RequestSerializer(connection , many=True )
        # send request list back to this user
        self.send_group(user.username , 'request.list', serialized.data)


    # to eenable friends accept eah other request
    def receive_request_accept(self, data):
	    
        username = data.get('username')
        # latest message subquery
        latest_message =    Message.objects.filter(
            connection=OuterRef('id').order_by('created')[:1]
        )
        try:
            connection = Connection.objects.get(
                sender_username=username,
                receiver=self.scope['user']
            ).annotate(
			    latest_text   = latest_message.values('text'),
			    latest_created = latest_message.values('created')
		).order_by(
			Coalesce('latest_created', 'updated').desc()
		)
        except Connection.DoesNotExist:
            print('Error :connection doesnt exists')
            return 
        # update the connection
        connection.accept = True
        connection.save()
        serialized = RequestSerializer(connection)
        # send accepted request to sender 
        self.send_group(
            connection.sender.username , 'request.accept' , serialized.data
        )
        # send accepted request to receiver
        self.send_group(
            connection.receiver.username , 'request.accept' , serialized.data
        )


   
    # function to enable the list out all a user friends 
    def receive_request_friend_list(self , data):
        user = self.scope['user']

        # Get connection for user
        connections = Connection.objects.filter(
            Q(sender=user )  |    Q( receiver=user),
            accepted=True
        )
        serialized = FriendSerializer(connections , context={'user:':user} , many=True)
        #send data back to requesting user
        self.send_group(user.username , 'friend.list'  , serialized.data)

    # to display all the messages of a user with another user
    def receive_message_list(self, data):
            user = self.scope['user']
            connectionId = data.get('connectionId')
            page=data.get('page')
            page_size = 15

            try:
                connection = Connection.objects.get(id=connectionId)
            except Connection.DoesNotExist:
                print('Error: couldnt find connection')
                return
            # Get messages
            messages = Message.objects.filter(
                connection=connection
            ).order_by('created')[page * page_size:(page + 1) * page_size]
            #serialized message
            serialized_messages = MessageSerializer(
                messages,
                context={
                    'user':user
                },
                many=True
            )
            # Get receipent friend
            recipient = connection.sender
            if connection.sender == user:
                recipient = connection.receiver

            # serialize friend
            serialized_friend = UserSerializer(recipient)
            messages_count = Message.objects.filter(
                connection=connection
            ).count()

            next_page = page + 1 if messages_count > (page + 1 ) * page_size else None

            data = {
			'messages': serialized_messages.data,
			'next': next_page,
			'friend': serialized_friend.data
		    }
		    # Send back to the requestor
            self.send_group(user.usernmae , 'message.list ' , data)

		
		
    # to enable a user send a messae and the other user will receive it realtime
    def receive_mesaage_send(self , data):
        user = self.scope['user']
        connectionId = data.get('connectionId')
        message_text = data.get('message')
        try:
            connection = Connection.objects.get(id=connectionId)
        except Connection.DoesNotExist:
            print('Error:couldnt find connection')
            return
        message = Message.objects.create(
            connection=connection,
            user=user,
            text=message_text
        )
        # get recipent friend
        recipient = connection.sender
        if connection.sender == user:
            recipient = connection.receiver
        
        # send new message back to sender
        serialized_message =    MessageSerializer(
            message,
            context={
                'user':user
            }
        )
        serialized_message = UserSerializer(recipient)
        data={
            'mesage':serialized_message.data,
            'friend': serialized_friend.data
        }
        self.send_group(user.username , 'message.send '  ,data)
        # send new message to receiver
        serialized_message = MessageSerializer(
            message,
            context={
                'user':recipient
            }
        )
        serialized_friend = UserSerializer(user)
        data={
            'mesage':serialized_message.data,
            'friend': serialized_friend.data
        }
        self.send_group(recipient.username , 'message.send' , data)



    def receive_message_type(self,data):
        user = self.scope['user']
        recipient_username = data.get('username')
        data = {
			'username': user.username
		}

        self.send_group(recipient_username , 'message.type' , data)



    # to allow user upload their thubnial /picture
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
        -source:where it originated from
        -data:what ever you want to send as a dict
        '''
    
        
    
        self.send(text_data = json.dumps(data))


