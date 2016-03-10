from kivy.uix.screenmanager import Screen
from kivy.storage.jsonstore import JsonStore
from kivy.clock import Clock
from kivy.app import App
from kivy.properties import ListProperty, StringProperty, NumericProperty

from os.path import join

# Self made components
from components import TagButton

from models import db, Gallery, GalleryTags, Search


class GalleryPreviewScreen(Screen):

    gallery_tags = ListProperty([])
    gallery_id = StringProperty("")
    pagecount = NumericProperty(0)
    gallery_name = StringProperty("")
    gallery_token = StringProperty("")
    gallery_thumb = StringProperty("")

    global data_dir

    def on_enter(self):
        gallerydata = db.query(Gallery).order_by(Gallery.id.desc()).first()
        print gallerydata.gallery_name
        tags = db.query(GalleryTags).filter_by(galleryid=gallerydata.id).all()
        taglist = []
        for tag in tags:
            taglist.append(tag.tag)
        self.gallery_id = gallerydata.gallery_id
        self.gallery_token = gallerydata.gallery_token
        self.pagecount = gallerydata.pagecount
        self.gallery_name = gallerydata.gallery_name
        self.gallery_tags = taglist
        self.gallery_thumb = gallerydata.gallery_thumb

        Clock.schedule_once(self.populate_tags)

    def populate_tags(self, *args):
        self.ids.tag_layout.clear_widgets()
        for tag in self.gallery_tags:
            taglabel = TagButton(tagname=tag)
            taglabel.bind(on_press=self.search_tag)
            self.ids.tag_layout.add_widget(taglabel)

    def view_gallery(self):
        App.get_running_app().root.next_screen("gallery_screen")

    def search_tag(self, instance):

        tag = instance.text
        search = Search(searchterm=tag)
        db.add(search)
        db.commit()
        App.get_running_app().root.next_screen("front_screen")
