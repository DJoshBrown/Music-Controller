from django.db.models.query import QuerySet
from django.http import response
from django.shortcuts import render
from rest_framework.exceptions import bad_request
from rest_framework.utils import serializer_helpers
from .serializers import RoomSerializer, CreateRoomSerializer, UpdateRoomSerializer
from rest_framework import generics, serializers, status
from .models import Room
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import JsonResponse


"""
The classes within the API file all control the get, post and patch requests specific to our app.
These request simply handle the opertion of the "Music Rooms" and do not actually handle the music itself.
That can be found within the spotify views.py file

"""


"""
This class creates a query to receive all of the objects within the room model.
This class will also contain the seralized fields from the 'Room' Object 
"""
class RoomView(generics.ListAPIView):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer

"""
This class is responsible for handle get requests to find specific rooms.  
It will look up an instance of a Room using its unique code.
It will return the rooms data and the session data, as well as a 200 status code.
It will return a 404 if the room is not found, or a 400 if there is an issue with the request made


Also note that this class will take and APIView parameter that will allow us to overwrite the 'get' method to perform 
the action we need it to.
"""
class GetRoom(APIView):
    serializer_class = RoomSerializer
    lookup_url_kwarg = 'code'

    def get(self, request, format=None):
        code = request.GET.get(self.lookup_url_kwarg)
        if code != None:
            room = Room.objects.filter(code=code)
            if len(room) >0: 
                data = RoomSerializer(room[0]).data
                data['is_host'] =self.request.session.session_key == room[0].host
                return Response(data, status= status.HTTP_200_OK)

            return Response({'Room not Found' : 'Invalid Room Code'}, status = status.HTTP_404_NOT_FOUND)
        return Response({'Bad Request' : 'Code Parameter Not Found'}, status = status.HTTP_400_BAD_REQUEST)
 

class JoinRoom(APIView):
    lookup_url_kwarg = 'code'

    def post(self, request, format=None):
        if not self.request.session.exists(self.request.session.session_key):
            self.request.session.create()
        
        code = request.data.get(self.lookup_url_kwarg)

        if code != None:
            room_result = Room.objects.filter(code=code)
            if len(room_result) > 0:
                room = room_result[0]
                self.request.session['room_code'] = code
                return Response({'message': 'Room Joined!'}, status.HTTP_200_OK)
            return Response({'Bad Request' : 'Invalid Room Code'}, status = status.HTTP_404_NOT_FOUND)

        return Response({'Bad Request' : 'Invalid Data, did not find code key'}, status = status.HTTP_400_BAD_REQUEST)




#APIView allows us to over-write such methods as get and post to create custom responses
class CreateRoomView(APIView):

    serializer_class= CreateRoomSerializer

    def post(self, request, format=None):
        if not self.request.session.exists(self.request.session.session_key):
            self.request.session.create()
        serializer= self.serializer_class(data=request.data)
        
        if serializer.is_valid():
            guest_can_pause = serializer.data.get('guest_can_pause')
            votes_to_skip = serializer.data.get('votes_to_skip')
            host = self.request.session.session_key 
           
            #queries to see if the host already exists
            queryset =Room.objects.filter(host=host)
            '''
            if the host does exist, allow the host to remain to the same, with the addition of the set 'guest_can_pause' 
            and 'votes_to skip' parameters for a given room
            '''
            if queryset.exists():
                room = queryset[0]
                room.guest_can_pause = guest_can_pause
                room.votes_to_skip = votes_to_skip
                room.save(update_fields =['guest_can_pause', 'votes_to_skip'] )
                self.request.session['room_code'] = room.code
                return Response(RoomSerializer(room).data, status=status.HTTP_200_OK)
            else:
                room = Room(host=host, guest_can_pause= guest_can_pause, votes_to_skip=votes_to_skip)
                room.save()
                self.request.session['room_code'] = room.code
                return Response(RoomSerializer(room).data, status=status.HTTP_201_CREATED)

        return Response({'Bad Request': 'Invalid data...'}, status=status.HTTP_400_BAD_REQUEST)


class UserInRoom(APIView):
    def get(self, request, format=None):
        if not self.request.session.exists(self.request.session.session_key):
            self.request.session.create()
        data = {
            'code' : self.request.session.get('room_code'),

        }
        
        return JsonResponse(data, status=status.HTTP_200_OK)


class LeaveRoom(APIView):
    def post(self, request, format=None):
        if 'room_code' in self.request.session:
            self.request.session.pop('room_code')
            host_id = self.request.session.session_key
            room_results = Room.objects.filter(host=host_id)

            if len(room_results) > 0 :
                room= room_results[0]
                room.delete()

        return Response({'Message' : 'Success'}, status=status.HTTP_200_OK)


class UpdateRoom(APIView):
    serializer_class= UpdateRoomSerializer
    
    def patch(self, request, format=None):
        if not self.request.session.exists(self.request.session.session_key):
            self.request.session.create()

        serializer = self.serializer_class(data = request.data)

        if serializer.is_valid():
            guest_can_pause = serializer.data.get('guest_can_pause')
            votes_to_skip = serializer.data.get('votes_to_skip')
            code = serializer.data.get('code')

            queryset = Room.objects.filter(code= code)
            
            if not queryset.exists():
                return Response({'Msg' : 'Room Not Found'}, status =status.HTTP_404_NOT_FOUND)
            
            room = queryset[0]
            user_id = self.request.session.session_key

            if room.host != user_id:
                return Response({'Msg' : 'Invalid Host: Permisson Denied'}, status=status.HTTP_403_FORBIDDEN)
            room.guest_can_pause = guest_can_pause
            room.votes_to_skip = votes_to_skip
            room.save(update_fields= ['guest_can_pause', 'votes_to_skip'])   
            return Response(RoomSerializer(room).data, status = status.HTTP_200_OK)    

        return Response({'Bad Request' : 'Invalid Data'}, status = status.HTTP_400_BAD_REQUEST)
