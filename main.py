import os, requests, time
from xml.etree import ElementTree
from flask import Flask,render_template, request,json,redirect,Response,send_file,send_from_directory
from lxml import html
import csv, json
from flask_cors import CORS
import requests


#
app = Flask(__name__)
CORS(app)

app.config.from_object("config")

app.config['CORS_HEADERS'] = 'Content-Type'


# '''
# If you prefer, you can hardcode your subscription key as a string and remove
# the provided conditional statement. However, we do recommend using environment
# variables to secure your subscription keys. The environment variable is
# set to SPEECH_SERVICE_KEY in our sample.
# For example:
# subscription_key = "Your-Key-Goes-Here"
# '''
if 'SPEECH_SERVICE_KEY' in os.environ:
    subscription_key = os.environ['SPEECH_SERVICE_KEY']
else:
    print('Environment variable for your subscription key is not set.')
    exit()

class TextToSpeech(object):
    def __init__(self, subscription_key):
        self.subscription_key = subscription_key
        self.tts = "Hello, How are you? How are you doing?"
        self.timestr = time.strftime("%Y%m%d-%H%M")
        self.access_token = None

    '''
    The TTS endpoint requires an access token. This method exchanges your
    subscription key for an access token that is valid for ten minutes.
    '''
    def get_token(self):
        fetch_token_url = "https://eastus.api.cognitive.microsoft.com/sts/v1.0/issuetoken"
        headers = {
            'Ocp-Apim-Subscription-Key': self.subscription_key
        }
        response = requests.post(fetch_token_url, headers=headers)
        self.access_token = str(response.text)

    def save_audio(self,text,fileName):
        base_url = 'https://eastus.tts.speech.microsoft.com/'
        path = 'cognitiveservices/v1'
        constructed_url = base_url + path
        headers = {
            'Authorization': 'Bearer ' + self.access_token,
            'Content-Type': 'application/ssml+xml',
            'X-Microsoft-OutputFormat': 'riff-24khz-16bit-mono-pcm',
            'User-Agent': 'text-to-speech'
        }
        xml_body = ElementTree.Element('speak', version='1.0')
        xml_body.set('{http://www.w3.org/XML/1998/namespace}lang', 'en-us')
        voice = ElementTree.SubElement(xml_body, 'voice')
        voice.set('{http://www.w3.org/XML/1998/namespace}lang', 'en-US')
        voice.set('rate', '+30.00%')
        #voice.set('name', 'en-US-JessaNeural') # Short name for 'Microsoft Server Speech Text to Speech Voice (en-US, Guy24KRUS)'
        voice.set('name', 'en-US-JessaNeural') # Short name for 'Microsoft Server Speech Text to Speech Voice (en-US, Guy24KRUS)'

        voice.text = text
        body = ElementTree.tostring(xml_body)

        response = requests.post(constructed_url, headers=headers, data=body)
        '''
        If a success response is returned, then the binary audio is written
        to file in your working directory. It is prefaced by sample and
        includes the date.
        '''
        if response.status_code == 200:
            with open(fileName + '.wav', 'wb') as audio:
                audio.write(response.content)
                print("\nStatus code: " + str(response.status_code) + "\nYour TTS is ready for playback.\n")
        else:
            print("\nStatus code: " + str(response.status_code) + "\nSomething went wrong. Check your subscription key and headers.\n")

# if __name__ == "__main__":
#     app = TextToSpeech(subscription_key)
#     app.get_token()
#     app.save_audio()

def createAudio(text,fileName):
    voiceApi = TextToSpeech(subscription_key)
    voiceApi.get_token()
    voiceApi.save_audio(text,fileName)

def bbcParse(link,title):

    page = requests.get(link)

    tree = html.fromstring(page.content)
    word = tree.xpath('//*[@class="story-body__inner"]')
    # print(word)
    # print(title)
    articleContent = {}
    articleContent["words"] = {}
    articleContent["language"] = "English";
    wordList = articleContent["words"]
    contentList = []
    pTag = word[0].xpath('//p')
    text = ''
    for x in range(len(pTag)):
        # print(pTag[x].text)

        if(x > 10 and x < len(pTag)-3 and pTag[x].text!=None):
            text = text + "   " +  pTag[x].text

        else:
            if(pTag[x].text != None):
                print("Trash: " + pTag[x].text)
    fileName = title
    text = text.replace(".", " ")
    createAudio(text,fileName)
    #createGoogleAudio(text,fileName)

@app.route('/articleLink', methods = ['POST'])
def getAPIKey():
    content = request.get_json()
    link = content["link"]
    title = content["title"]
    response = {}
    print(link)
    bbcParse(link,title)
    response["fileName"] = title
    return JSONEncoder().encode(response)

@app.route('/<file>')
def download_file(file):
    path_to_file = file + ".wav"

    return send_file(
     path_to_file,
     mimetype="audio/wav",
     as_attachment=True,
     attachment_filename=file + ".wav")

def createGoogleAudio(text,fileName):
    from google.cloud import texttospeech

    # Instantiates a client
    client = texttospeech.TextToSpeechClient()

    # Set the text input to be synthesized
    synthesis_input = texttospeech.types.SynthesisInput(text=text)

    # Build the voice request, select the language code ("en-US") and the ssml
    # voice gender ("neutral")
    voice = texttospeech.types.VoiceSelectionParams(
        language_code='en-US',
        ssml_gender=texttospeech.enums.SsmlVoiceGender.NEUTRAL)

    # Select the type of audio file you want returned
    audio_config = texttospeech.types.AudioConfig(
        audio_encoding=texttospeech.enums.AudioEncoding.MP3)

    # Perform the text-to-speech request on the text input with the selected
    # voice parameters and audio file type
    response = client.synthesize_speech(synthesis_input, voice, audio_config)

    # The response's audio_content is binary.
    with open(fileName + '.wav', 'wb') as out:
        # Write the response to the output file.
        out.write(response.audio_content)
    print("google audio done")

class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return json.JSONEncoder.default(self, o)


if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    voiceApi = TextToSpeech(subscription_key)
    voiceApi.get_token()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
