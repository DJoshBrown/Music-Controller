
from django.shortcuts import redirect, render
from rest_framework.response import Response
from rest_framework.settings import reload_api_settings
from .credentials import REDIRECT_URI, CLIENT_ID, CLIENT_SECRET
from rest_framework.views import APIView
from requests import Request, post 
from rest_framework import status
from .util import *
from api.models import Room 
from .models import Vote
# Create your views here.

class AuthURL (APIView):
    def get (self, request, format=None):
        #This is the information we want to access from spotify API (full info can be found from spotify developer pages)
        scopes = 'user-read-playback-state user-modify-playback-state user-read-currently-playing'

        url = Request('GET', 'https://accounts.spotify.com/authorize', params={
        'scope':scopes, 
        'response_type':'code',
        'redirect_uri':REDIRECT_URI,
        'client_id': CLIENT_ID
        }).prepare().url


        return Response({'url':url}, status=status.HTTP_200_OK)


def spotify_callback(request, format=None):

    code= request.GET.get('code')
    error= request.GET.get('error')

    response = post('https://accounts.spotify.com/api/token', data= {
        
        'grant_type':'authorization_code',
        'code':code,
        'redirect_uri': REDIRECT_URI,
        'client_id': CLIENT_ID, 
        'client_secret': CLIENT_SECRET
    }).json()

    access_token = response.get('access_token')
    token_type= response.get('token_type')
    refresh_token= response.get('refresh_token')
    expires_in= response.get('expires_in')
    error= response.get('error')

    if not request.session.exists(request.session.session_key):
        request.session.create()

    update_or_create_user_tokens(request.session.session_key, access_token, token_type, expires_in, refresh_token)

    return redirect('frontend:')

class IsAuthenticated(APIView):
    def get(self, request, format=None):
        is_authenticated= is_spotify_authenticated(self.request.session.session_key)
        return Response({'status':is_authenticated}, status.HTTP_200_OK)


class CurrentSong(APIView):
    def get(self, request, format=None):
        room_code = self.request.session.get('room_code')
        room = Room.objects.filter(code= room_code)
        if room.exists():
            room = room[0]
        else :
            return Response({"This is the else"}, status= status.HTTP_404_NOT_FOUND)
        host = room.host
        endpoint = "player/currently-playing"
        response = execute_spotify_api_request(host, endpoint)

        if 'error' in response or 'item' not in response:
            return Response({}, status= status.HTTP_204_NO_CONTENT)
        
        item = response.get('item')
        duration = item.get('duration_ms')
        progress = response.get('progress_ms')
        album_cover = item.get('album').get('images')[0].get('url')
        is_playing = response.get('is_playing')
        song_id = item.get('id')

        artist_string= ""

        ''' This is a very teachable moment in how to format and concatinate string. Great example for future references
            also note that the item.get('artists') is pluralize. This is also a very important point to review when working with
            API's in gerneal and making sure that you have correctly entered the key value you wish to access. In this case, the key 
            value is 'artists' and not 'artist'. This may also lead to some confusion upon coming back to this function, as the loop variable
            is artist. Bare this in mind when working with APIs in the future
        ''' 

        for i, artist in enumerate (item.get('artists')):
            if i > 0:
                artist_string += ", "
            name = artist.get('name')
            artist_string += name 
        
        '''Another very teachable moment here. Here, we have created our own custom song object to return to the front end
        This includes the 'artist_string'  we created above. This is a key part of working with API's and RADStack in general
        In the back end, we can process the logic in python, with the help of django, while handling all of the front end tasks in 
        javascript, with the help of react. We then create a response object, to send our song, as well as a status code to be displayed
        on out website. 
        
        This is a very important principle, please ensure you look back at this when studying API's in the future ''' 

        votes =len(Vote.objects.filter(room=room, song_id=song_id))
        song = { 
            'title' : item.get('name'),
            'artists': artist_string,
            'duration': duration,
            'time' : progress,
            'image_url':album_cover,
            'is_playing': is_playing,
            'votes': votes, 
            'votes_required':room.votes_to_skip,
            'id':song_id

        }
        self.update_room_song(room, song_id)
        return Response(song, status= status.HTTP_200_OK)

    def update_room_song(self, room, song_id):
        current_song = room.current_song

        if current_song != song_id:
            room.current_song = song_id
            room.save(update_fields=['current_song'])
            votes = Vote.objects.filter(room=room).delete()

class PauseSong(APIView): 
    def put(self, response, format=None):
        room_code = self.request.session.get('room_code')
        room = Room.objects.filter(code=room_code)[0]
        if self.request.session.session_key  == room.host or room.guest_can_pause:
            pause_song(room.host)
            return Response({}, status=status.HTTP_204_NO_CONTENT)
        return Response({}, status=status.HTTP_403_FORBIDDEN)

class PlaySong(APIView): 
    def put(self, response, format=None):
        room_code = self.request.session.get('room_code')
        room = Room.objects.filter(code = room_code)[0]
        if self.request.session.session_key  == room.host or room.guest_can_pause:
            play_song(room.host)
            return Response({}, status=status.HTTP_204_NO_CONTENT)
        return Response({}, status=status.HTTP_403_FORBIDDEN)

class SkipSong(APIView):
    def post(self, request, format=None):
        room_code = self.request.session.get('room_code')
        room = Room.objects.filter(code=room_code)[0]
        votes = Vote.objects.filter(room=room, song_id=room.current_song)
        votes_needed = room.votes_to_skip

        if self.request.session.session_key == room.host or len(votes)+1 >=votes_needed:
            votes.delete()
            skip_song(room.host)
        else:
            vote = Vote(user = self.request.session.session_key, room =room, song_id= room.current_song)
            vote.save()


        return Response({}, status=status.HTTP_204_NO_CONTENT)