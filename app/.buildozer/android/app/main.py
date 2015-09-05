# -*- coding: utf8 -*-
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.image import AsyncImage as Image
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.properties import StringProperty, ListProperty, NumericProperty, ObjectProperty
from kivy.storage.jsonstore import JsonStore
from kivy.clock import Clock
from kivy.uix.progressbar import ProgressBar

from os.path import join
import os
from functools import partial
from BeautifulSoup import BeautifulSoup as BS

import requests
import json
import re

data_dir = ""


class ThumbButton(ButtonBehavior, Image):

    gallery_id = StringProperty("")
    gallery_token = StringProperty("")
    gallery_name = StringProperty("")
    pagecount = NumericProperty(0)


class FrontScreen(Screen):

    global data_dir

    pb = ProgressBar(max=4500)
    gallery_thumbs = ListProperty([])
    gidlist = ListProperty([])
    # Because I am a n00b at using API's like these, I keep getting hour-bans
    # because of too many requests, as they do not like web scraping/api-usage
    # proxyip = "104.197.107.186:3128"
    # proxyip = "209.66.193.244:8080"
    # works at 23:17proxyip = "168.62.191.144:3128"
    searchword = StringProperty("")



    def on_enter(self):

        searchstore = JsonStore("searchstore.json")
        if searchstore.exists("searchstring"):
            self.searchword = searchstore["searchstring"]["searchphrase"]
        else:
            self.searchword = ""

        self.ids.main_layout.clear_widgets()

        self.pb.value = 0
        self.gallery_thumbs = []

        for i in range(10):
            Clock.schedule_once(self.increasepb, i)

        self.ids.main_layout.add_widget(self.pb)

        Clock.schedule_once(self.populate_front, 5)

    def increasepb(self, state):
        self.pb.value += 450
        if self.pb.value == 4500:
            self.ids.main_layout.remove_widget(self.pb)

    def enter_gallery(self, state):
        gallery_store = JsonStore(join(data_dir, 'gallerystore.json'))
        galleryinfo = [state.gallery_id, state.gallery_token, state.pagecount,
                       state.gallery_name]
        gallery_store.put("current_gallery", galleryinfo=galleryinfo)
        self.manager.current = "gallery_screen"

    def populate_front(self, state):
        # ehentai link
        headers = {'User-agent': 'Mozilla/5.0'}
        r = requests.get("http://g.e-hentai.org/?f_doujinshi=0&f_manga=0&f_artistcg=0&f_gamecg=0&f_western=0&f_non-h=1&f_imageset=0&f_cosplay=0&f_asianporn=0&f_misc=0&f_search="+self.searchword+"&f_apply=Apply+Filter", headers=headers)
        # pure html of ehentai link
        data = r.text

        soup = BS(data, fromEncoding='utf8')
        gallerylinks = []

        # grabs all the divs with class it5 which denotes the gallery on the
        # page
        for link in soup.findAll('div', {'class': 'it5'}):
            # grabs all the links, should only be gallery links as of 29th of
            # august 2015
            gallerylinks.append(link.find('a')["href"])

        for link in gallerylinks:
            splitlink = link.split('/')
            # grab the gallery token
            gtoken = splitlink[-2]
            # grab the gallery id
            gid = splitlink[-3]
            self.gidlist.append([gid, gtoken])
            print(self.gidlist)

        headers = {"Content-type": "application/json", "Accept": "text/plain",
                   'User-agent': 'Mozilla/5.0'}
        payload = {
            "method": "gdata",
            "gidlist": self.gidlist
            }

        Clock.schedule_once(partial(self.grabthumbs, headers, payload), 1)

    def grabthumbs(self, headers, payload, *largs):
        r = requests.post("http://g.e-hentai.org/api.php",
                          data=json.dumps(payload), headers=headers)
        requestdump = r.text
        requestdump.rstrip(os.linesep)
        requestjson = json.loads(requestdump)
        i = 0
        for gallery in requestjson["gmetadata"]:
            Clock.schedule_once(partial(self.add_button, gallery), i)
            i += 1

    def add_button(self, gallery, *largs):
        gallerybutton = ThumbButton(
            source=gallery["thumb"],
            gallery_id=str(gallery["gid"]),
            gallery_token=str(gallery["token"]),
            pagecount=int(gallery["filecount"]),
            gallery_name=gallery["title"], allow_stretch=True)
        gallerybutton.bind(on_press=self.enter_gallery)
        buttoncontainer = BoxLayout(orientation="horizontal")
        buttoncontainer.add_widget(gallerybutton)
        buttoncontainer.add_widget(ScrollableTitle(titletext=gallery["title"]))
        self.ids.main_layout.add_widget(buttoncontainer)


class ScrollableTitle(ScrollView):

    titletext = StringProperty("")


class GalleryScreen(Screen):

    gallery_id = StringProperty("")
    gallery_token = StringProperty("")
    pagelinks = ListProperty([])
    pagecount = NumericProperty(0)
    gallery_name = StringProperty("")

    global data_dir

    def on_enter(self):
        gallery_store = JsonStore(join(data_dir, 'gallerystore.json'))
        if gallery_store.exists("current_gallery"):
            galleryinfo = gallery_store.get("current_gallery")
            self.gallery_id = galleryinfo["galleryinfo"][0]
            self.gallery_token = galleryinfo["galleryinfo"][1]
            self.pagecount = galleryinfo["galleryinfo"][2]
            self.gallery_name = galleryinfo["galleryinfo"][3]
            print self.gallery_name
        self.populate_gallery()

    def populate_gallery(self):
        # change placehold.it with
        gallerypages = float(self.pagecount) / float(40)
        pageregex = re.compile('http://g.e-hentai.org/s/\S{10}/\d{6}-\d+')

        if gallerypages.is_integer():
            print(gallerypages)
        else:
            gallerypages += 1
            print(gallerypages)

        headers = {'User-agent': 'Mozilla/5.0'}
        for i in range(int(gallerypages)):
            galleryrequest = requests.get("http://g.e-hentai.org/g/{}/{}/?p={}".format(self.gallery_id, self.gallery_token, i), headers=headers)

            soup = BS(galleryrequest.text)

            for a in soup.findAll(name="a", attrs={"href": pageregex}):
                self.pagelinks.append(a["href"])
            print(self.pagelinks)

        pagetimer = 0
        for page in self.pagelinks:
            Clock.schedule_once(partial(self.grab_image, page), 5*pagetimer)
            pagetimer += 1

    def grab_image(self, i, *largs):
        print(i)
        headers = {'User-agent': 'Mozilla/5.0'}
        pagerequest = requests.get(url=i, headers=headers)

        soup = BS(pagerequest.text)

        srctag = soup.findAll(name="img", attrs={"id": "img"})
        print srctag
        for each in srctag:
            src = each["src"]
        image = GalleryImage(source=src, allow_stretch=True)
        self.ids.gallery_carousel.add_widget(image)


class GalleryImage(Image):
    pass


class SearchPopup(Popup):

    global data_dir

    def savesearch(self):
        print(self.ids.searchstring.text)
        searchstore = JsonStore('searchstore.json')
        searchquery = self.ids.searchstring.text
        searchstore.put("searchstring", searchphrase=searchquery)
        self.dismiss()


class SadpandaRoot(BoxLayout):

    def __init__(self, **kwargs):
        super(SadpandaRoot, self).__init__(**kwargs)
        # list of previous screens
        self.screen_list = []

    def next_screen(self, neoscreen):

        if self.ids.sadpanda_screen_manager.current not in self.screen_list:
            self.screen_list.append(self.ids.sadpanda_screen_manager.current)

        self.ids.sadpanda_screen_manager.current = neoscreen

    def goto_front(self, instance):
        self.ids.sadpanda_screen_manager.current = "front_screen"

    def search_popup(self):
        spopup = SearchPopup()
        print(spopup)
        spopup.bind(on_dismiss=self.goto_front)
        spopup.open()


class SadpandaApp(App):

    def __init__(self, **kwargs):
        super(SadpandaApp, self).__init__(**kwargs)
        global data_dir
        data_dir = getattr(self, 'user_data_dir')

    def on_pause(self):
        return True

    def build(self):
        return SadpandaRoot()

if __name__ == "__main__":
    SadpandaApp().run()