# NextcloudClient helper class to handle API interactions
import requests
from lxml import etree
from urllib.parse import urljoin, quote
import os
import json
import threading
from gi.repository import GLib, Gtk, Adw, Pango, Gio
from .extensions import NewelleExtension
from .tools import create_io_tool, Tool, ToolResult
from .handlers.extra_settings import ExtraSettings

class NextcloudBaseWidget(Gtk.Box):
    """Base class for Nextcloud widgets with common styling."""
    
    def __init__(self, title: str, icon_name: str, subtitle: str = ""):
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=0,
            margin_top=10,
            margin_bottom=10,
            margin_start=10,
            margin_end=10,
        )
        self.add_css_class("card")
        
        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header.set_margin_top(12)
        header.set_margin_bottom(8)
        header.set_margin_start(16)
        header.set_margin_end(16)
        
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(24)
        icon.add_css_class("accent")
        header.append(icon)
        
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title_box.set_hexpand(True)
        
        self.title_label = Gtk.Label(label=title, xalign=0)
        self.title_label.add_css_class("title-4")
        title_box.append(self.title_label)
        
        if subtitle:
            self.subtitle_label = Gtk.Label(label=subtitle, xalign=0)
            self.subtitle_label.add_css_class("dim-label")
            self.subtitle_label.add_css_class("caption")
            title_box.append(self.subtitle_label)
        else:
            self.subtitle_label = None
        
        header.append(title_box)
        
        # Spinner for loading state
        self.spinner = Gtk.Spinner()
        self.spinner.set_spinning(True)
        header.append(self.spinner)
        
        self.append(header)
        
        # Separator
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self.append(sep)
        
        # Content area
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.append(self.content_box)
    
    def set_loading(self, loading: bool):
        self.spinner.set_spinning(loading)
        self.spinner.set_visible(loading)
    
    def set_error(self, message: str):
        self.set_loading(False)
        error_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        error_box.set_margin_top(16)
        error_box.set_margin_bottom(16)
        error_box.set_margin_start(16)
        error_box.set_margin_end(16)
        error_box.set_halign(Gtk.Align.CENTER)
        
        icon = Gtk.Image.new_from_icon_name("dialog-error-symbolic")
        icon.add_css_class("error")
        error_box.append(icon)
        
        label = Gtk.Label(label=message)
        label.add_css_class("dim-label")
        error_box.append(label)
        
        self.content_box.append(error_box)


class FileListWidget(NextcloudBaseWidget):
    """Widget for displaying Nextcloud file listings."""
    
    def __init__(self, path: str = ""):
        display_path = path if path else "/"
        super().__init__(
            title="Nextcloud Files",
            icon_name="folder-symbolic",
            subtitle=f"Path: {display_path}"
        )
        self.path = path
        self.files = []
    
    def set_files(self, files: list):
        """Set files to display. files is list of dicts with name, is_directory, size."""
        self.set_loading(False)
        self.files = files
        
        if not files:
            empty_label = Gtk.Label(label="No files found")
            empty_label.add_css_class("dim-label")
            empty_label.set_margin_top(24)
            empty_label.set_margin_bottom(24)
            self.content_box.append(empty_label)
            return
        
        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        listbox.add_css_class("boxed-list")
        listbox.set_margin_start(12)
        listbox.set_margin_end(12)
        listbox.set_margin_top(8)
        listbox.set_margin_bottom(12)
        
        for f in files:
            row = Adw.ActionRow()
            
            # Icon
            if f.get("is_directory"):
                row.set_icon_name("folder-symbolic")
                row.add_css_class("folder-row")
            else:
                # Choose icon based on extension
                name = f.get("name", "")
                icon = self._get_file_icon(name)
                row.set_icon_name(icon)
            
            row.set_title(f.get("name", "Unknown"))
            
            # Size/type subtitle
            if f.get("is_directory"):
                row.set_subtitle("Folder")
            else:
                size = int(f.get("size", 0))
                row.set_subtitle(self._format_size(size))
            
            listbox.append(row)
        
        self.content_box.append(listbox)
    
    def _get_file_icon(self, filename: str) -> str:
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        icons = {
            "pdf": "x-office-document-symbolic",
            "doc": "x-office-document-symbolic",
            "docx": "x-office-document-symbolic",
            "txt": "text-x-generic-symbolic",
            "md": "text-x-generic-symbolic",
            "jpg": "image-x-generic-symbolic",
            "jpeg": "image-x-generic-symbolic",
            "png": "image-x-generic-symbolic",
            "gif": "image-x-generic-symbolic",
            "mp3": "audio-x-generic-symbolic",
            "mp4": "video-x-generic-symbolic",
            "zip": "package-x-generic-symbolic",
            "py": "text-x-script-symbolic",
            "js": "text-x-script-symbolic",
        }
        return icons.get(ext, "text-x-generic-symbolic")
    
    def _format_size(self, size: int) -> str:
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.1f} GB"


class NoteWidget(NextcloudBaseWidget):
    """Widget for displaying a Nextcloud note."""
    
    def __init__(self, title: str = "", category: str = ""):
        super().__init__(
            title=title or "Note",
            icon_name="accessories-text-editor-symbolic",
            subtitle=f"Category: {category}" if category else ""
        )
    
    def set_content(self, content: str):
        self.set_loading(False)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_max_content_height(300)
        scrolled.set_propagate_natural_height(True)
        scrolled.set_margin_start(16)
        scrolled.set_margin_end(16)
        scrolled.set_margin_top(8)
        scrolled.set_margin_bottom(16)
        scrolled.set_size_request(400, 400)
        
        text_view = Gtk.TextView()
        text_view.set_editable(False)
        text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        text_view.set_cursor_visible(False)
        text_view.get_buffer().set_text(content)
        text_view.add_css_class("card")
        text_view.set_left_margin(12)
        text_view.set_right_margin(12)
        text_view.set_top_margin(12)
        text_view.set_bottom_margin(12)
        
        scrolled.set_child(text_view)
        self.content_box.append(scrolled)


class NotesListWidget(NextcloudBaseWidget):
    """Widget for displaying a list of notes."""
    
    def __init__(self):
        super().__init__(
            title="Nextcloud Notes",
            icon_name="accessories-text-editor-symbolic",
            subtitle="Your notes"
        )
    
    def set_notes(self, notes: list):
        """notes: list of dicts with id, title, category."""
        self.set_loading(False)
        
        if not notes:
            empty_label = Gtk.Label(label="No notes found")
            empty_label.add_css_class("dim-label")
            empty_label.set_margin_top(24)
            empty_label.set_margin_bottom(24)
            self.content_box.append(empty_label)
            return
        
        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        listbox.add_css_class("boxed-list")
        listbox.set_margin_start(12)
        listbox.set_margin_end(12)
        listbox.set_margin_top(8)
        listbox.set_margin_bottom(12)
        
        for note in notes:
            row = Adw.ActionRow()
            row.set_icon_name("text-x-generic-symbolic")
            row.set_title(note.get("title", "Untitled"))
            
            category = note.get("category", "")
            note_id = note.get("id", "")
            row.set_subtitle(f"#{note_id}" + (f" • {category}" if category else ""))
            
            listbox.append(row)
        
        self.content_box.append(listbox)


class DeckBoardWidget(NextcloudBaseWidget):
    """Widget for displaying Deck boards."""
    
    def __init__(self):
        super().__init__(
            title="Deck Boards",
            icon_name="view-paged-symbolic",
            subtitle="Kanban boards"
        )
    
    def set_boards(self, boards: list):
        """boards: list of dicts with id, title."""
        self.set_loading(False)
        
        if not boards:
            empty_label = Gtk.Label(label="No boards found")
            empty_label.add_css_class("dim-label")
            empty_label.set_margin_top(24)
            empty_label.set_margin_bottom(24)
            self.content_box.append(empty_label)
            return
        
        flow_box = Gtk.FlowBox()
        flow_box.set_selection_mode(Gtk.SelectionMode.NONE)
        flow_box.set_homogeneous(True)
        flow_box.set_column_spacing(8)
        flow_box.set_row_spacing(8)
        flow_box.set_min_children_per_line(1)
        flow_box.set_max_children_per_line(3)
        flow_box.set_margin_start(12)
        flow_box.set_margin_end(12)
        flow_box.set_margin_top(12)
        flow_box.set_margin_bottom(12)
        
        for board in boards:
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            card.add_css_class("card")
            card.set_margin_start(4)
            card.set_margin_end(4)
            card.set_margin_top(4)
            card.set_margin_bottom(4)
            
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            inner.set_margin_start(16)
            inner.set_margin_end(16)
            inner.set_margin_top(16)
            inner.set_margin_bottom(16)
            
            icon = Gtk.Image.new_from_icon_name("view-paged-symbolic")
            icon.set_pixel_size(32)
            icon.add_css_class("accent")
            inner.append(icon)
            
            title = Gtk.Label(label=board.get("title", "Untitled"))
            title.add_css_class("title-4")
            title.set_ellipsize(Pango.EllipsizeMode.END)
            inner.append(title)
            
            board_id = Gtk.Label(label=f"ID: {board.get('id', '')}")
            board_id.add_css_class("dim-label")
            board_id.add_css_class("caption")
            inner.append(board_id)
            
            card.append(inner)
            flow_box.append(card)
        
        self.content_box.append(flow_box)


class DeckStacksWidget(NextcloudBaseWidget):
    """Widget for displaying Deck stacks (columns)."""
    
    def __init__(self, board_id: int):
        super().__init__(
            title="Deck Stacks",
            icon_name="view-dual-symbolic",
            subtitle=f"Board #{board_id}"
        )
        self.board_id = board_id
    
    def set_stacks(self, stacks: list):
        """stacks: list of dicts with id, title."""
        self.set_loading(False)
        
        if not stacks:
            empty_label = Gtk.Label(label="No stacks found")
            empty_label.add_css_class("dim-label")
            empty_label.set_margin_top(24)
            empty_label.set_margin_bottom(24)
            self.content_box.append(empty_label)
            return
        
        # Horizontal scrollable stack view
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        scrolled.set_margin_start(12)
        scrolled.set_margin_end(12)
        scrolled.set_margin_top(8)
        scrolled.set_margin_bottom(12)
        
        stack_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        
        for stack in stacks:
            column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            column.add_css_class("card")
            column.set_size_request(160, -1)
            
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            inner.set_margin_start(12)
            inner.set_margin_end(12)
            inner.set_margin_top(12)
            inner.set_margin_bottom(12)
            
            title = Gtk.Label(label=stack.get("title", "Untitled"))
            title.add_css_class("heading")
            title.set_ellipsize(Pango.EllipsizeMode.END)
            inner.append(title)
            
            stack_id = Gtk.Label(label=f"ID: {stack.get('id', '')}")
            stack_id.add_css_class("dim-label")
            stack_id.add_css_class("caption")
            inner.append(stack_id)
            
            column.append(inner)
            stack_box.append(column)
        
        scrolled.set_child(stack_box)
        self.content_box.append(scrolled)


class DeckCardsWidget(NextcloudBaseWidget):
    """Widget for displaying cards in a stack."""
    
    def __init__(self, board_id: int, stack_id: int):
        super().__init__(
            title="Cards",
            icon_name="view-list-symbolic",
            subtitle=f"Stack #{stack_id}"
        )
        self.board_id = board_id
        self.stack_id = stack_id
    
    def set_cards(self, cards: list):
        """cards: list of dicts with id, title, description."""
        self.set_loading(False)
        
        if not cards:
            empty_label = Gtk.Label(label="No cards found")
            empty_label.add_css_class("dim-label")
            empty_label.set_margin_top(24)
            empty_label.set_margin_bottom(24)
            self.content_box.append(empty_label)
            return
        
        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        listbox.add_css_class("boxed-list")
        listbox.set_margin_start(12)
        listbox.set_margin_end(12)
        listbox.set_margin_top(8)
        listbox.set_margin_bottom(12)
        
        for card in cards:
            row = Adw.ActionRow()
            row.set_icon_name("view-list-bullet-symbolic")
            row.set_title(card.get("title", "Untitled"))
            
            desc = card.get("description", "")
            if desc:
                # Truncate long descriptions
                if len(desc) > 50:
                    desc = desc[:50] + "..."
                row.set_subtitle(desc)
            else:
                row.set_subtitle(f"Card #{card.get('id', '')}")
            
            listbox.append(row)
        
        self.content_box.append(listbox)


class CalendarEventsWidget(NextcloudBaseWidget):
    """Widget for displaying calendar events."""
    
    def __init__(self, calendar_name: str = "", date_range: str = ""):
        super().__init__(
            title="Calendar Events",
            icon_name="x-office-calendar-symbolic",
            subtitle=calendar_name or "Events"
        )
        self.calendar_name = calendar_name
    
    def set_events(self, events: list):
        """events: list of dicts with summary, dtstart."""
        self.set_loading(False)
        
        if not events:
            empty_label = Gtk.Label(label="No events found")
            empty_label.add_css_class("dim-label")
            empty_label.set_margin_top(24)
            empty_label.set_margin_bottom(24)
            self.content_box.append(empty_label)
            return
        
        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        listbox.add_css_class("boxed-list")
        listbox.set_margin_start(12)
        listbox.set_margin_end(12)
        listbox.set_margin_top(8)
        listbox.set_margin_bottom(12)
        
        for event in events:
            row = Adw.ActionRow()
            row.set_icon_name("alarm-symbolic")
            row.set_title(event.get("summary", "No Title"))
            
            dtstart = event.get("dtstart", "")
            if dtstart:
                row.set_subtitle(dtstart)
            
            listbox.append(row)
        
        self.content_box.append(listbox)


class CalendarsListWidget(NextcloudBaseWidget):
    """Widget for displaying list of calendars."""
    
    def __init__(self):
        super().__init__(
            title="Calendars",
            icon_name="x-office-calendar-symbolic",
            subtitle="Your calendars"
        )
    
    def set_calendars(self, calendars: list):
        """calendars: list of dicts with name, href."""
        self.set_loading(False)
        
        if not calendars:
            empty_label = Gtk.Label(label="No calendars found")
            empty_label.add_css_class("dim-label")
            empty_label.set_margin_top(24)
            empty_label.set_margin_bottom(24)
            self.content_box.append(empty_label)
            return
        
        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        listbox.add_css_class("boxed-list")
        listbox.set_margin_start(12)
        listbox.set_margin_end(12)
        listbox.set_margin_top(8)
        listbox.set_margin_bottom(12)
        
        for cal in calendars:
            row = Adw.ActionRow()
            row.set_icon_name("x-office-calendar-symbolic")
            row.set_title(cal.get("name", "Untitled"))
            row.set_subtitle(cal.get("href", ""))
            
            listbox.append(row)
        
        self.content_box.append(listbox)


class ContactsWidget(NextcloudBaseWidget):
    """Widget for displaying contacts."""
    
    def __init__(self, addressbook: str = "", page: int = 1, total_pages: int = 1):
        super().__init__(
            title="Contacts",
            icon_name="avatar-default-symbolic",
            subtitle=f"{addressbook or 'Address Book'} (Page {page}/{total_pages})"
        )
        self.addressbook = addressbook
    
    def set_contacts(self, contacts: list):
        """contacts: list of dicts with fn, email, tel, href, uid."""
        self.set_loading(False)
        
        if not contacts:
            empty_label = Gtk.Label(label="No contacts found")
            empty_label.add_css_class("dim-label")
            empty_label.set_margin_top(24)
            empty_label.set_margin_bottom(24)
            self.content_box.append(empty_label)
            return
        
        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        listbox.add_css_class("boxed-list")
        listbox.set_margin_start(12)
        listbox.set_margin_end(12)
        listbox.set_margin_top(8)
        listbox.set_margin_bottom(12)
        
        for contact in contacts:
            row = Adw.ActionRow()
            row.set_icon_name("avatar-default-symbolic")
            
            name = contact.get("fn") or "Unknown Name"
            row.set_title(name)
            
            details = []
            email = contact.get("email")
            if email: details.append(email)
            tel = contact.get("tel")
            if tel: details.append(tel)
            
            if details:
                row.set_subtitle(" • ".join(details))
            
            listbox.append(row)
        
        self.content_box.append(listbox)


class ContactDetailWidget(NextcloudBaseWidget):
    """Widget for displaying contact details."""
    
    def __init__(self, name: str = ""):
        super().__init__(
            title=name or "Contact Details",
            icon_name="avatar-default-symbolic",
            subtitle="Contact Info"
        )
    
    def set_details(self, details: dict):
        self.set_loading(False)
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.set_margin_start(16)
        content.set_margin_end(16)
        content.set_margin_top(8)
        content.set_margin_bottom(16)
        
        # Helper to add rows
        def add_row(label_text, value_text):
            if not value_text: return
            row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            lbl = Gtk.Label(label=label_text, xalign=0)
            lbl.add_css_class("caption")
            lbl.add_css_class("dim-label")
            val = Gtk.Label(label=value_text, xalign=0, wrap=True)
            val.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
            val.set_selectable(True)
            row.append(lbl)
            row.append(val)
            content.append(row)
            content.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        add_row("Full Name", details.get("fn"))
        add_row("Email", details.get("email"))
        add_row("Phone", details.get("tel"))
        add_row("Organization", details.get("org"))
        add_row("Address", details.get("adr"))
        add_row("Note", details.get("note"))
        
        # Remove last separator if exists
        children = list(content)
        if children and isinstance(children[-1], Gtk.Separator):
            content.remove(children[-1])

        self.content_box.append(content)


class AddressBooksWidget(NextcloudBaseWidget):
    """Widget for displaying address books."""
    
    def __init__(self):
        super().__init__(
            title="Address Books",
            icon_name="x-office-address-book-symbolic",
            subtitle="Contact folders"
        )
    
    def set_addressbooks(self, books: list):
        """books: list of dicts with name, href."""
        self.set_loading(False)
        
        if not books:
            empty_label = Gtk.Label(label="No address books found")
            empty_label.add_css_class("dim-label")
            empty_label.set_margin_top(24)
            empty_label.set_margin_bottom(24)
            self.content_box.append(empty_label)
            return
        
        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        listbox.add_css_class("boxed-list")
        listbox.set_margin_start(12)
        listbox.set_margin_end(12)
        listbox.set_margin_top(8)
        listbox.set_margin_bottom(12)
        
        for book in books:
            row = Adw.ActionRow()
            row.set_icon_name("x-office-address-book-symbolic")
            row.set_title(book.get("name", "Untitled"))
            row.set_subtitle(book.get("href", ""))
            
            listbox.append(row)
        
        self.content_box.append(listbox)


class RecipeWidget(NextcloudBaseWidget):
    """Widget for displaying a recipe."""
    
    def __init__(self, name: str = ""):
        super().__init__(
            title=name or "Recipe",
            icon_name="emoji-food-symbolic",
            subtitle="Cookbook"
        )
    
    def set_recipe(self, name: str, description: str, ingredients: str):
        self.set_loading(False)
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.set_margin_start(16)
        content.set_margin_end(16)
        content.set_margin_top(8)
        content.set_margin_bottom(16)
        
        if description:
            desc_label = Gtk.Label(label=description, xalign=0, wrap=True)
            desc_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
            content.append(desc_label)
        
        if ingredients:
            ing_header = Gtk.Label(label="Ingredients", xalign=0)
            ing_header.add_css_class("heading")
            content.append(ing_header)
            
            ing_label = Gtk.Label(label=ingredients, xalign=0, wrap=True)
            ing_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
            content.append(ing_label)
        
        self.content_box.append(content)


class RecipesListWidget(NextcloudBaseWidget):
    """Widget for displaying list of recipes."""
    
    def __init__(self):
        super().__init__(
            title="Cookbook Recipes",
            icon_name="emoji-food-symbolic",
            subtitle="Your recipes"
        )
    
    def set_recipes(self, recipes: list):
        """recipes: list of dicts with id, name."""
        self.set_loading(False)
        
        if not recipes:
            empty_label = Gtk.Label(label="No recipes found")
            empty_label.add_css_class("dim-label")
            empty_label.set_margin_top(24)
            empty_label.set_margin_bottom(24)
            self.content_box.append(empty_label)
            return
        
        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        listbox.add_css_class("boxed-list")
        listbox.set_margin_start(12)
        listbox.set_margin_end(12)
        listbox.set_margin_top(8)
        listbox.set_margin_bottom(12)
        
        for recipe in recipes:
            row = Adw.ActionRow()
            row.set_icon_name("emoji-food-symbolic")
            row.set_title(recipe.get("name", "Untitled"))
            row.set_subtitle(f"ID: {recipe.get('id', '')}")
            
            listbox.append(row)
        
        self.content_box.append(listbox)


class SuccessWidget(NextcloudBaseWidget):
    """Widget for displaying successful operations."""
    
    def __init__(self, operation: str, message: str):
        super().__init__(
            title=operation,
            icon_name="emblem-ok-symbolic",
            subtitle="Completed successfully"
        )
        self.set_loading(False)
        
        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        content.set_margin_start(16)
        content.set_margin_end(16)
        content.set_margin_top(16)
        content.set_margin_bottom(16)
        content.set_halign(Gtk.Align.CENTER)
        
        icon = Gtk.Image.new_from_icon_name("emblem-ok-symbolic")
        icon.set_pixel_size(24)
        icon.add_css_class("success")
        content.append(icon)
        
        label = Gtk.Label(label=message, wrap=True)
        label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        content.append(label)
        
        self.content_box.append(content)

class NextcloudClient:
    def __init__(self, url, username, password):
        self.url = url.rstrip('/') + '/'
        self.username = username
        self.password = password
        self.auth = requests.auth.HTTPBasicAuth(username, password)
        self.session = requests.Session()
        self.session.auth = self.auth

    def _get_webdav_url(self, path):
        # path relative to user files root
        # WebDAV custom endpoint: remote.php/dav/files/USERNAME/path
        # Ensure path doesn't start with / if we join it
        path = path.lstrip('/')
        # Use quote to encode path segments correctly
        return urljoin(self.url, f"remote.php/dav/files/{self.username}/{quote(path)}")

    def _get_notes_api_url(self, endpoint):
        # API v1: index.php/apps/notes/api/v1/notes
        return urljoin(self.url, f"index.php/apps/notes/api/v1/{endpoint}")

    def _get_deck_api_url(self, endpoint):
        # index.php/apps/deck/api/v1.0/
        return urljoin(self.url, f"index.php/apps/deck/api/v1.0/{endpoint}")

    def _get_cookbook_api_url(self, endpoint):
        # index.php/apps/cookbook/api/v1/
        return urljoin(self.url, f"index.php/apps/cookbook/api/v1/{endpoint}")

    def _get_caldav_url(self, endpoint=""):
        # remote.php/dav/calendars/USERNAME/
        endpoint = endpoint.lstrip('/')
        return urljoin(self.url, f"remote.php/dav/calendars/{self.username}/{endpoint}")

    def _get_carddav_url(self, endpoint=""):
        # remote.php/dav/addressbooks/users/USERNAME/
        endpoint = endpoint.lstrip('/')
        return urljoin(self.url, f"remote.php/dav/addressbooks/users/{self.username}/{endpoint}")

    def list_files(self, path=""):
        path = path.lstrip('/')
        url = self._get_webdav_url(path)
        
        # PROPFIND
        headers = {'Depth': '1'}
        response = self.session.request('PROPFIND', url, headers=headers)
        if response.status_code == 404:
            return f"Error: Path '{path}' not found."
        response.raise_for_status()

        # Parse XML
        # Namespace usually: {DAV:}
        try:
            tree = etree.fromstring(response.content)
            # ElementTree usually has namespaces.
            # We want to extract displayname or href, content type, size.
            items = []
            ns = {'d': 'DAV:'}
            for response_elem in tree.findall('{DAV:}response'):
                href = response_elem.find('{DAV:}href').text
                # Decode href
                from urllib.parse import unquote
                href = unquote(href)
                
                # Check for collection
                propstat = response_elem.find('{DAV:}propstat')
                prop = propstat.find('{DAV:}prop')
                
                is_collection = False
                resourcetype = prop.find('{DAV:}resourcetype')
                if resourcetype is not None and resourcetype.find('{DAV:}collection') is not None:
                    is_collection = True

                displayname = prop.find('{DAV:}displayname')
                name = displayname.text if displayname is not None else os.path.basename(href.rstrip('/'))
                
                contentlength = prop.find('{DAV:}getcontentlength')
                size = contentlength.text if contentlength is not None else "0"

                items.append({
                    "name": name,
                    "href": href,
                    "is_directory": is_collection,
                    "size": size
                })
            
            # Format output
            output = f"Listing of {path}:\n"
            for item in items:
                type_str = "[DIR]" if item['is_directory'] else "[FILE]"
                output += f"{type_str} {item['name']} ({item['size']} bytes)\n"
            return output
        except Exception as e:
            return f"Error parsing WebDAV response: {str(e)}"

    def read_file(self, path):
        path = path.lstrip('/')
        url = self._get_webdav_url(path)
        response = self.session.get(url)
        if response.status_code == 404:
             return f"Error: File '{path}' not found."
        response.raise_for_status()
        return response.text

    def write_file(self, path, content):
        path = path.lstrip('/')
        url = self._get_webdav_url(path)
        response = self.session.put(url, data=content.encode('utf-8'))
        response.raise_for_status()
        return f"Successfully wrote to '{path}'."

    def delete_file(self, path):
        path = path.lstrip('/')
        url = self._get_webdav_url(path)
        response = self.session.delete(url)
        if response.status_code == 404:
             return f"Error: File '{path}' not found."
        response.raise_for_status()
        return f"Successfully deleted '{path}'."

    def create_directory(self, path):
        path = path.lstrip('/')
        url = self._get_webdav_url(path)
        response = self.session.request('MKCOL', url)
        if response.status_code == 405: # Method Not Allowed - likely exists
             return f"Directory '{path}' already exists or not allowed."
        response.raise_for_status()
        return f"Successfully created directory '{path}'."

    # Notes API
    def list_notes(self):
        url = self._get_notes_api_url("notes")
        response = self.session.get(url)
        if response.status_code == 404:
             return "Notes app not found or not enabled on this Nextcloud instance."
        response.raise_for_status()
        notes = response.json()
        
        output = "Notes:\n"
        for note in notes:
            output += f"- ID: {note['id']}, Title: {note['title']}, Category: {note['category']}\n"
        return output

    def get_note(self, note_id):
        url = self._get_notes_api_url(f"notes/{note_id}")
        response = self.session.get(url)
        response.raise_for_status()
        note = response.json()
        return f"Title: {note['title']}\nCategory: {note['category']}\nContent:\n{note['content']}"

    def create_note(self, title, content, category=""):
        url = self._get_notes_api_url("notes")
        payload = {"title": title, "content": content, "category": category}
        response = self.session.post(url, json=payload)
        response.raise_for_status()
        note = response.json()
        return f"Note created with ID: {note['id']}"

    def delete_note(self, note_id):
        url = self._get_notes_api_url(f"notes/{note_id}")
        response = self.session.delete(url)
        response.raise_for_status()
        return f"Note {note_id} deleted."

    # Calendar (CalDAV)
    def list_calendars(self):
        url = self._get_caldav_url()
        headers = {'Depth': '1'}
        response = self.session.request('PROPFIND', url, headers=headers)
        response.raise_for_status()
        try:
            tree = etree.fromstring(response.content)
            calendars = []
            for response_elem in tree.findall('{DAV:}response'):
                href = response_elem.find('{DAV:}href').text
                propstat = response_elem.find('{DAV:}propstat')
                prop = propstat.find('{DAV:}prop')
                displayname = prop.find('{DAV:}displayname')
                
                # Filter for calendars (usually have {urn:ietf:params:xml:ns:caldav}calendar or similar)
                # For simplicity, we list collections under the user's caldav root
                resourcetype = prop.find('{DAV:}resourcetype')
                if resourcetype is not None and resourcetype.find('{urn:ietf:params:xml:ns:caldav}calendar') is not None:
                     name = displayname.text if displayname is not None else os.path.basename(href.rstrip('/'))
                     calendars.append({"name": name, "href": href})

            output = "Calendars:\n"
            for cal in calendars:
                output += f"- {cal['name']} (Path: {cal['href']})\n"
            return output
        except Exception as e:
            return f"Error listing calendars: {str(e)}"

    def create_calendar_event(self, calendar_name, title, start_dt, end_dt, description=""):
        # Very basic iCalendar generation
        import uuid
        uid = str(uuid.uuid4())
        # format: 20231027T100000Z
        ical = f"BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\nUID:{uid}\nSUMMARY:{title}\nDTSTART:{start_dt}\nDTEND:{end_dt}\nDESCRIPTION:{description}\nEND:VEVENT\nEND:VCALENDAR"
        
        url = self._get_caldav_url(f"{calendar_name}/{uid}.ics")
        headers = {'Content-Type': 'text/calendar; charset=utf-8'}
        response = self.session.put(url, data=ical, headers=headers)
        response.raise_for_status()
        return f"Event '{title}' created in calendar '{calendar_name}'."

    # Contacts (CardDAV)
    def list_addressbooks(self):
        url = self._get_carddav_url()
        headers = {'Depth': '1'}
        response = self.session.request('PROPFIND', url, headers=headers)
        response.raise_for_status()
        try:
            tree = etree.fromstring(response.content)
            books = []
            for response_elem in tree.findall('{DAV:}response'):
                href = response_elem.find('{DAV:}href').text
                propstat = response_elem.find('{DAV:}propstat')
                prop = propstat.find('{DAV:}prop')
                displayname = prop.find('{DAV:}displayname')
                
                resourcetype = prop.find('{DAV:}resourcetype')
                if resourcetype is not None and resourcetype.find('{urn:ietf:params:xml:ns:carddav}addressbook') is not None:
                     name = displayname.text if displayname is not None else os.path.basename(href.rstrip('/'))
                     books.append({"name": name, "href": href})

            output = "Address Books:\n"
            for book in books:
                output += f"- {book['name']} (Path: {book['href']})\n"
            return output
        except Exception as e:
            return f"Error listing address books: {str(e)}"

    def list_contacts(self, addressbook_name, page=1, limit=30, search_term=None):
        result, error = self.list_contacts_raw(addressbook_name, page, limit, search_term)
        if error: return error
        
        contacts = result['contacts']
        total = result['total']
        total_pages = (total + limit - 1) // limit if limit else 1
        
        output = f"Contacts in {addressbook_name} (Page {page}/{total_pages}, {total} total):\n"
        for contact in contacts:
            line = f"- {contact.get('fn', 'Unknown')} "
            details = []
            if contact.get("email"): details.append(f"<{contact['email']}>")
            if contact.get("tel"): details.append(f"[Tel: {contact['tel']}]")
            if search_term: details.append(f"(Ref: {contact['href']})")
            
            if details:
                line += " ".join(details)
            output += line + "\n"
        return output

    def get_contact(self, addressbook_name, contact_filename):
        data, error = self.get_contact_raw(addressbook_name, contact_filename)
        if error: return error
        
        output = f"Contact Details for {data.get('fn', 'Unknown')}:\n"
        if data.get('email'): output += f"Email: {data['email']}\n"
        if data.get('tel'): output += f"Phone: {data['tel']}\n"
        if data.get('org'): output += f"Organization: {data['org']}\n"
        if data.get('adr'): output += f"Address: {data['adr']}\n"
        if data.get('note'): output += f"Note: {data['note']}\n"
        return output

    def _parse_vcard(self, vcard_text):
        """Simple VCard parser."""
        data = {}
        # Unfold lines
        lines = vcard_text.replace('\r\n ', '').replace('\n ', '').splitlines()
        for line in lines:
            if ':' not in line: continue
            key, val = line.split(':', 1)
            key_parts = key.split(';')
            key_name = key_parts[0].upper()
            
            # Simple decoding
            val = val.strip()
            
            if key_name == 'FN': data['fn'] = val
            elif key_name == 'EMAIL': data['email'] = val
            elif key_name == 'TEL': data['tel'] = val
            elif key_name == 'ORG': data['org'] = val
            elif key_name == 'NOTE': data['note'] = val
            elif key_name == 'ADR': 
                # ADR values are semicolon separated
                parts = val.split(';')
                # filtering empty parts
                addr = ", ".join([p for p in parts if p])
                data['adr'] = addr
        return data

    # Deck
    def list_deck_boards(self):
        url = self._get_deck_api_url("boards")
        response = self.session.get(url)
        response.raise_for_status()
        boards = response.json()
        output = "Deck Boards:\n"
        for board in boards:
            output += f"- ID: {board['id']}, Title: {board['title']}\n"
        return output

    def create_deck_board(self, title, color="000000"):
        url = self._get_deck_api_url("boards")
        response = self.session.post(url, json={"title": title, "color": color})
        response.raise_for_status()
        board = response.json()
        return f"Deck board created with ID: {board['id']}"

    def list_deck_stacks(self, board_id):
        url = self._get_deck_api_url(f"boards/{board_id}/stacks")
        response = self.session.get(url)
        response.raise_for_status()
        stacks = response.json()
        output = f"Stacks for Board {board_id}:\n"
        for stack in stacks:
            output += f"- ID: {stack['id']}, Title: {stack['title']}\n"
        return output

    def list_deck_cards(self, board_id, stack_id):
        url = self._get_deck_api_url(f"boards/{board_id}/stacks/{stack_id}")
        response = self.session.get(url)
        response.raise_for_status()
        stack = response.json()
        cards = stack.get('cards', [])
        output = f"Cards in Stack {stack_id}:\n"
        for card in cards:
            output += f"- ID: {card['id']}, Title: {card['title']}, Description: {card.get('description', '')}\n"
        return output

    # Cookbook
    def list_recipes(self):
        url = self._get_cookbook_api_url("recipes")
        response = self.session.get(url)
        response.raise_for_status()
        recipes = response.json()
        output = "Recipes:\n"
        for recipe in recipes:
            output += f"- {recipe['name']} (ID: {recipe['id']})\n"
        return output

    def get_recipe(self, recipe_id):
        url = self._get_cookbook_api_url(f"recipes/{recipe_id}")
        response = self.session.get(url)
        response.raise_for_status()
        recipe = response.json()
        return f"Recipe: {recipe['name']}\nDescription: {recipe.get('description', '')}\nIngredients:\n{recipe.get('ingredients', '')}"

    def create_recipe(self, name, description="", ingredients="", instructions=""):
        url = self._get_cookbook_api_url("recipes")
        # Nextcloud Cookbook expects ingredients and instructions as lists
        if isinstance(ingredients, str):
            ingredients = [i.strip() for i in ingredients.split('\n') if i.strip()]
        if isinstance(instructions, str):
            instructions = [i.strip() for i in instructions.split('\n') if i.strip()]
            
        data = {
            "name": name,
            "description": description,
            "ingredients": ingredients,
            "instructions": instructions
        }
        response = self.session.post(url, json=data)
        response.raise_for_status()
        recipe = response.json()
        recipe_id = recipe['id'] if isinstance(recipe, dict) else recipe
        return f"Recipe created with ID: {recipe_id}"

    def import_recipe(self, url):
        import_url = self._get_cookbook_api_url("import")
        response = self.session.post(import_url, json={"url": url})
        response.raise_for_status()
        recipe = response.json()
        recipe_id = recipe.get('id', 'unknown') if isinstance(recipe, dict) else recipe
        return f"Recipe imported with ID: {recipe_id}"

    # Extended Deck Methods
    def create_deck_stack(self, board_id, title, order=0):
        url = self._get_deck_api_url(f"boards/{board_id}/stacks")
        response = self.session.post(url, json={"title": title, "order": order})
        response.raise_for_status()
        return f"Stack created: {response.json().get('title')}"

    def update_deck_stack(self, board_id, stack_id, title=None, order=None):
        url = self._get_deck_api_url(f"boards/{board_id}/stacks/{stack_id}")
        data = {}
        if title: data["title"] = title
        if order is not None: data["order"] = order
        response = self.session.put(url, json=data)
        response.raise_for_status()
        return f"Stack {stack_id} updated."

    def delete_deck_stack(self, board_id, stack_id):
        url = self._get_deck_api_url(f"boards/{board_id}/stacks/{stack_id}")
        response = self.session.delete(url)
        response.raise_for_status()
        return f"Stack {stack_id} deleted."

    def create_deck_card(self, board_id, stack_id, title, description="", ctype="plain", order=0, duedate=None):
        url = self._get_deck_api_url(f"boards/{board_id}/stacks/{stack_id}/cards")
        data = {
            "title": title,
            "description": description,
            "type": ctype,
            "order": order
        }
        if duedate: data["duedate"] = duedate
        response = self.session.post(url, json=data)
        response.raise_for_status()
        card = response.json()
        return f"Card created with ID: {card['id']}"

    def update_deck_card(self, board_id, stack_id, card_id, title=None, description=None, order=None, duedate=None, archived=None):
        url = self._get_deck_api_url(f"boards/{board_id}/stacks/{stack_id}/cards/{card_id}")
        data = {}
        if title: data["title"] = title
        if description is not None: data["description"] = description
        if order is not None: data["order"] = order
        if duedate is not None: data["duedate"] = duedate
        if archived is not None: data["archived"] = archived
        
        response = self.session.put(url, json=data)
        response.raise_for_status()
        return f"Card {card_id} updated."
    
    def reorder_deck_card(self, board_id, stack_id, card_id, order, target_stack_id=None):
        url = self._get_deck_api_url(f"boards/{board_id}/stacks/{stack_id}/cards/{card_id}")
        data = {"order": order}
        if target_stack_id:
             data["stackId"] = target_stack_id
        
        response = self.session.put(url, json=data)
        response.raise_for_status()
        return f"Card {card_id} reordered."

    def delete_deck_card(self, board_id, stack_id, card_id):
        url = self._get_deck_api_url(f"boards/{board_id}/stacks/{stack_id}/cards/{card_id}")
        response = self.session.delete(url)
        response.raise_for_status()
        return f"Card {card_id} deleted."

    def create_deck_label(self, board_id, title, color):
        url = self._get_deck_api_url(f"boards/{board_id}/labels")
        response = self.session.post(url, json={"title": title, "color": color})
        response.raise_for_status()
        label = response.json()
        return f"Label created with ID: {label['id']}"

    def update_deck_label(self, board_id, label_id, title=None, color=None):
        url = self._get_deck_api_url(f"boards/{board_id}/labels/{label_id}")
        data = {}
        if title: data["title"] = title
        if color: data["color"] = color
        response = self.session.put(url, json=data)
        response.raise_for_status()
        return f"Label {label_id} updated."

    def delete_deck_label(self, board_id, label_id):
        url = self._get_deck_api_url(f"boards/{board_id}/labels/{label_id}")
        response = self.session.delete(url)
        response.raise_for_status()
        return f"Label {label_id} deleted."

    def assign_deck_label(self, board_id, stack_id, card_id, label_id):
        url = self._get_deck_api_url(f"boards/{board_id}/stacks/{stack_id}/cards/{card_id}/assignLabel")
        response = self.session.put(url, json={"labelId": label_id})
        response.raise_for_status()
        return f"Label {label_id} assigned to card {card_id}."

    def remove_deck_label(self, board_id, stack_id, card_id, label_id):
        url = self._get_deck_api_url(f"boards/{board_id}/stacks/{stack_id}/cards/{card_id}/removeLabel")
        response = self.session.put(url, json={"labelId": label_id})
        response.raise_for_status()
        return f"Label {label_id} removed from card {card_id}."

    def assign_deck_user(self, board_id, stack_id, card_id, user_id):
        url = self._get_deck_api_url(f"boards/{board_id}/stacks/{stack_id}/cards/{card_id}/assignUser")
        response = self.session.put(url, json={"userId": user_id})
        response.raise_for_status()
        return f"User {user_id} assigned to card {card_id}."

    def remove_deck_user(self, board_id, stack_id, card_id, user_id):
        url = self._get_deck_api_url(f"boards/{board_id}/stacks/{stack_id}/cards/{card_id}/unassignUser")
        response = self.session.put(url, json={"userId": user_id})
        response.raise_for_status()
        return f"User {user_id} unassigned from card {card_id}."

    # Extended Calendar
    def list_calendar_events(self, calendar_name, start, end):
        # start, end -> YYYYMMDDTHHMMSSZ
        url = self._get_caldav_url(calendar_name)
        
        # XML date format
        body = f'''
        <c:calendar-query xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
            <d:prop>
                <d:getetag />
                <c:calendar-data />
            </d:prop>
            <c:filter>
                <c:comp-filter name="VCALENDAR">
                    <c:comp-filter name="VEVENT">
                        <c:time-range start="{start}" end="{end}"/>
                    </c:comp-filter>
                </c:comp-filter>
            </c:filter>
        </c:calendar-query>
        '''
        
        headers = {
            'Depth': '1',
            'Content-Type': 'application/xml; charset=utf-8'
        }
        response = self.session.request('REPORT', url, data=body, headers=headers)
        response.raise_for_status()
        
        try:
            tree = etree.fromstring(response.content)
            events = []
            for response_elem in tree.findall('{DAV:}response'):
                href = response_elem.find('{DAV:}href').text
                propstat = response_elem.find('{DAV:}propstat')
                prop = propstat.find('{DAV:}prop')
                caldata = prop.find('{urn:ietf:params:xml:ns:caldav}calendar-data')
                
                if caldata is not None:
                     events.append({"href": href, "data": caldata.text})
            
            output = f"Events in {calendar_name} ({start} to {end}):\n"
            for ef in events:
                # Basic parsing string search for Summary and Time
                data = ef['data']
                summary = "No Title"
                dtstart = ""
                for line in data.splitlines():
                    if line.startswith("SUMMARY:"): summary = line[8:]
                    if line.startswith("DTSTART:"): dtstart = line[8:]
                output += f"- {summary} ({dtstart})\n"
            return output
        except Exception as e:
            return f"Error listing events: {str(e)}"

    def delete_calendar_event(self, calendar_name, event_filename):
        # event_filename needs to be the resource name e.g. "uuid.ics"
        url = self._get_caldav_url(f"{calendar_name}/{event_filename}")
        response = self.session.delete(url)
        response.raise_for_status()
        return f"Event {event_filename} deleted."

    def get_calendar_event(self, calendar_name, event_filename):
        url = self._get_caldav_url(f"{calendar_name}/{event_filename}")
        response = self.session.get(url)
        response.raise_for_status()
        return response.text

    # Raw data methods for widget support
    def list_files_raw(self, path=""):
        """Return raw file list data for widget use."""
        path = path.lstrip('/')
        url = self._get_webdav_url(path)
        headers = {'Depth': '1'}
        response = self.session.request('PROPFIND', url, headers=headers)
        if response.status_code == 404:
            return None, f"Error: Path '{path}' not found."
        response.raise_for_status()

        try:
            from urllib.parse import unquote
            tree = etree.fromstring(response.content)
            items = []
            for response_elem in tree.findall('{DAV:}response'):
                href = response_elem.find('{DAV:}href').text
                href = unquote(href)
                propstat = response_elem.find('{DAV:}propstat')
                prop = propstat.find('{DAV:}prop')
                
                is_collection = False
                resourcetype = prop.find('{DAV:}resourcetype')
                if resourcetype is not None and resourcetype.find('{DAV:}collection') is not None:
                    is_collection = True

                displayname = prop.find('{DAV:}displayname')
                name = displayname.text if displayname is not None else os.path.basename(href.rstrip('/'))
                
                contentlength = prop.find('{DAV:}getcontentlength')
                size = contentlength.text if contentlength is not None else "0"

                items.append({
                    "name": name,
                    "href": href,
                    "is_directory": is_collection,
                    "size": size
                })
            return items, None
        except Exception as e:
            return None, f"Error parsing WebDAV response: {str(e)}"

    def list_notes_raw(self):
        """Return raw notes data."""
        url = self._get_notes_api_url("notes")
        response = self.session.get(url)
        if response.status_code == 404:
            return None, "Notes app not found."
        response.raise_for_status()
        return response.json(), None

    def get_note_raw(self, note_id):
        """Return raw note data."""
        url = self._get_notes_api_url(f"notes/{note_id}")
        response = self.session.get(url)
        response.raise_for_status()
        return response.json(), None

    def list_calendars_raw(self):
        """Return raw calendars data."""
        url = self._get_caldav_url()
        headers = {'Depth': '1'}
        response = self.session.request('PROPFIND', url, headers=headers)
        response.raise_for_status()
        try:
            tree = etree.fromstring(response.content)
            calendars = []
            for response_elem in tree.findall('{DAV:}response'):
                href = response_elem.find('{DAV:}href').text
                propstat = response_elem.find('{DAV:}propstat')
                prop = propstat.find('{DAV:}prop')
                displayname = prop.find('{DAV:}displayname')
                resourcetype = prop.find('{DAV:}resourcetype')
                if resourcetype is not None and resourcetype.find('{urn:ietf:params:xml:ns:caldav}calendar') is not None:
                    name = displayname.text if displayname is not None else os.path.basename(href.rstrip('/'))
                    calendars.append({"name": name, "href": href})
            return calendars, None
        except Exception as e:
            return None, f"Error: {str(e)}"

    def list_calendar_events_raw(self, calendar_name, start, end):
        """Return raw calendar events data."""
        url = self._get_caldav_url(calendar_name)
        body = f'''
        <c:calendar-query xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
            <d:prop>
                <d:getetag />
                <c:calendar-data />
            </d:prop>
            <c:filter>
                <c:comp-filter name="VCALENDAR">
                    <c:comp-filter name="VEVENT">
                        <c:time-range start="{start}" end="{end}"/>
                    </c:comp-filter>
                </c:comp-filter>
            </c:filter>
        </c:calendar-query>
        '''
        headers = {'Depth': '1', 'Content-Type': 'application/xml; charset=utf-8'}
        response = self.session.request('REPORT', url, data=body, headers=headers)
        response.raise_for_status()
        
        try:
            tree = etree.fromstring(response.content)
            events = []
            for response_elem in tree.findall('{DAV:}response'):
                href = response_elem.find('{DAV:}href').text
                propstat = response_elem.find('{DAV:}propstat')
                prop = propstat.find('{DAV:}prop')
                caldata = prop.find('{urn:ietf:params:xml:ns:caldav}calendar-data')
                
                if caldata is not None:
                    data = caldata.text
                    summary = "No Title"
                    dtstart = ""
                    for line in data.splitlines():
                        if line.startswith("SUMMARY:"): summary = line[8:]
                        if line.startswith("DTSTART:"): dtstart = line[8:]
                    events.append({"summary": summary, "dtstart": dtstart, "href": href})
            return events, None
        except Exception as e:
            return None, f"Error: {str(e)}"

    def list_addressbooks_raw(self):
        """Return raw addressbooks data."""
        url = self._get_carddav_url()
        headers = {'Depth': '1'}
        response = self.session.request('PROPFIND', url, headers=headers)
        response.raise_for_status()
        try:
            tree = etree.fromstring(response.content)
            books = []
            for response_elem in tree.findall('{DAV:}response'):
                href = response_elem.find('{DAV:}href').text
                propstat = response_elem.find('{DAV:}propstat')
                prop = propstat.find('{DAV:}prop')
                displayname = prop.find('{DAV:}displayname')
                resourcetype = prop.find('{DAV:}resourcetype')
                if resourcetype is not None and resourcetype.find('{urn:ietf:params:xml:ns:carddav}addressbook') is not None:
                    name = displayname.text if displayname is not None else os.path.basename(href.rstrip('/'))
                    books.append({"name": name, "href": href})
            return books, None
        except Exception as e:
            return None, f"Error: {str(e)}"

    def list_contacts_raw(self, addressbook_name, page=1, limit=30, search_term=None):
        """Return raw contacts data using addressbook-query."""
        url = self._get_carddav_url(addressbook_name)
        
        # Addressbook query to get FN, EMAIL, TEL, UID
        body = '''
        <c:addressbook-query xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:carddav">
            <d:prop>
                <d:getetag />
                <c:address-data>
                    <c:prop name="FN"/>
                    <c:prop name="EMAIL"/>
                    <c:prop name="TEL"/>
                    <c:prop name="UID"/>
                </c:address-data>
            </d:prop>
        </c:addressbook-query>
        '''
        
        headers = {
            'Depth': '1', 
            'Content-Type': 'application/xml; charset=utf-8'
        }
        
        try:
            response = self.session.request('REPORT', url, data=body, headers=headers)
            response.raise_for_status()
            
            tree = etree.fromstring(response.content)
            contacts = []
            
            for response_elem in tree.findall('{DAV:}response'):
                href = response_elem.find('{DAV:}href').text
                propstat = response_elem.find('{DAV:}propstat')
                prop = propstat.find('{DAV:}prop')
                adata = prop.find('{urn:ietf:params:xml:ns:carddav}address-data')
                
                if adata is not None and adata.text:
                    vcard = self._parse_vcard(adata.text)
                    vcard['href'] = os.path.basename(href)
                    
                    # Search filtering
                    if search_term:
                        term = search_term.lower()
                        match = False
                        if term in vcard.get('fn', '').lower(): match = True
                        if term in vcard.get('email', '').lower(): match = True
                        if term in vcard.get('tel', '').lower(): match = True
                        if not match: continue
                    
                    contacts.append(vcard)
            
            # Sort by name
            contacts.sort(key=lambda x: x.get('fn', '').lower())
            
            # Pagination
            total = len(contacts)
            start = (page - 1) * limit
            end = start + limit
            paged_contacts = contacts[start:end]
            
            return {'contacts': paged_contacts, 'total': total}, None
            
        except Exception as e:
            print(f"Error in list_contacts_raw: {str(e)}") # Debug
            # Fallback to PROPFIND if REPORT fails (though unlikely for Nextcloud)
            try:
                # Basic PROPFIND fallback
                headers = {'Depth': '1'}
                response = self.session.request('PROPFIND', url, headers=headers)
                response.raise_for_status()
                tree = etree.fromstring(response.content)
                contacts = []
                for response_elem in tree.findall('{DAV:}response'):
                    href = response_elem.find('{DAV:}href').text
                    if href.endswith('.vcf'):
                        name = os.path.basename(href).replace('.vcf', '').replace('-', ' ').title()
                        contacts.append({'fn': name, 'href': os.path.basename(href)})
                
                if search_term:
                    contacts = [c for c in contacts if search_term.lower() in c['fn'].lower()]
                
                contacts.sort(key=lambda x: x['fn'])
                
                total = len(contacts)
                paged = contacts[(page-1)*limit : (page-1)*limit + limit]
                return {'contacts': paged, 'total': total}, None
            except Exception as e2:
                return None, f"Error listing contacts: {str(e)} / {str(e2)}"

    def get_contact_raw(self, addressbook_name, contact_filename):
        """Get full contact details."""
        url = self._get_carddav_url(f"{addressbook_name}/{contact_filename}")
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return self._parse_vcard(response.text), None
        except Exception as e:
            return None, f"Error getting contact: {str(e)}"

    def list_deck_boards_raw(self):
        """Return raw deck boards data."""
        url = self._get_deck_api_url("boards")
        response = self.session.get(url)
        response.raise_for_status()
        return response.json(), None

    def list_deck_stacks_raw(self, board_id):
        """Return raw stacks data."""
        url = self._get_deck_api_url(f"boards/{board_id}/stacks")
        response = self.session.get(url)
        response.raise_for_status()
        return response.json(), None

    def list_deck_cards_raw(self, board_id, stack_id):
        """Return raw cards data."""
        url = self._get_deck_api_url(f"boards/{board_id}/stacks/{stack_id}")
        response = self.session.get(url)
        response.raise_for_status()
        stack = response.json()
        return stack.get('cards', []), None

    def list_recipes_raw(self):
        """Return raw recipes data."""
        url = self._get_cookbook_api_url("recipes")
        response = self.session.get(url)
        response.raise_for_status()
        return response.json(), None

    def get_recipe_raw(self, recipe_id):
        """Return raw recipe data."""
        url = self._get_cookbook_api_url(f"recipes/{recipe_id}")
        response = self.session.get(url)
        response.raise_for_status()
        return response.json(), None


class NextcloudExtension(NewelleExtension):
    name = "NextCloud"
    id="nextcloud"

    def get_extra_settings(self) -> list:
        return [
            ExtraSettings.EntrySetting("nextcloud_url", "Nextcloud URL", "URL of your Nextcloud instance (e.g. https://cloud.example.com)", ""),
            ExtraSettings.EntrySetting("nextcloud_username", "Username", "Nextcloud username", ""),
            ExtraSettings.EntrySetting("nextcloud_password", "Password / App Password", "Nextcloud password or App Password (recommended)", "", password=True),
        ]

    def _get_client(self):
        url = self.get_setting("nextcloud_url")
        username = self.get_setting("nextcloud_username")
        password = self.get_setting("nextcloud_password")
        
        if not url or not username or not password:
            return None, "Nextcloud configuration missing. Please check settings."
            
        try:
            client = NextcloudClient(url, username, password)
            return client, None
        except Exception as e:
            return None, str(e)

    # ========== Widget-enabled tools ==========

    def nc_list_files_widget(self, path: str = ""):
        """List files with visual widget."""
        result = ToolResult()
        widget = FileListWidget(path)
        result.set_widget(widget)
        
        def fetch():
            client, error = self._get_client()
            if error:
                GLib.idle_add(widget.set_error, error)
                result.set_output(error)
                return
            
            try:
                files, err = client.list_files_raw(path)
                if err:
                    GLib.idle_add(widget.set_error, err)
                    result.set_output(err)
                else:
                    GLib.idle_add(widget.set_files, files)
                    output = client.list_files(path)
                    result.set_output(output)
            except Exception as e:
                GLib.idle_add(widget.set_error, str(e))
                result.set_output(f"Error: {str(e)}")
        
        thread = threading.Thread(target=fetch)
        thread.start()
        return result

    def nc_list_files_restore(self, tool_uuid: str, path: str = ""):
        """Restore file list widget."""
        result = ToolResult()
        widget = FileListWidget(path)
        output = self.ui_controller.get_tool_result_by_id(tool_uuid)
        widget.set_loading(False)
        result.set_widget(widget)
        result.set_output(output)
        return result

    def nc_list_notes_widget(self):
        """List notes with visual widget."""
        result = ToolResult()
        widget = NotesListWidget()
        result.set_widget(widget)
        
        def fetch():
            client, error = self._get_client()
            if error:
                GLib.idle_add(widget.set_error, error)
                result.set_output(error)
                return
            
            try:
                notes, err = client.list_notes_raw()
                if err:
                    GLib.idle_add(widget.set_error, err)
                    result.set_output(err)
                else:
                    GLib.idle_add(widget.set_notes, notes)
                    output = client.list_notes()
                    result.set_output(output)
            except Exception as e:
                GLib.idle_add(widget.set_error, str(e))
                result.set_output(f"Error: {str(e)}")
        
        thread = threading.Thread(target=fetch)
        thread.start()
        return result

    def nc_list_notes_restore(self, tool_uuid: str):
        """Restore notes list widget."""
        result = ToolResult()
        widget = NotesListWidget()
        output = self.ui_controller.get_tool_result_by_id(tool_uuid)
        widget.set_loading(False)
        result.set_widget(widget)
        result.set_output(output)
        return result

    def nc_get_note_widget(self, note_id: int):
        """Get note with visual widget."""
        result = ToolResult()
        widget = NoteWidget()
        result.set_widget(widget)
        
        def fetch():
            client, error = self._get_client()
            if error:
                GLib.idle_add(widget.set_error, error)
                result.set_output(error)
                return
            
            try:
                note, err = client.get_note_raw(note_id)
                if err:
                    GLib.idle_add(widget.set_error, err)
                    result.set_output(err)
                else:
                    GLib.idle_add(widget.set_content, note.get('content', ''))
                    output = client.get_note(note_id)
                    result.set_output(output)
            except Exception as e:
                GLib.idle_add(widget.set_error, str(e))
                result.set_output(f"Error: {str(e)}")
        
        thread = threading.Thread(target=fetch)
        thread.start()
        return result

    def nc_get_note_restore(self, tool_uuid: str, note_id: int):
        """Restore note widget."""
        result = ToolResult()
        widget = NoteWidget()
        output = self.ui_controller.get_tool_result_by_id(tool_uuid)
        widget.set_loading(False)
        result.set_widget(widget)
        result.set_output(output)
        return result

    def nc_list_calendars_widget(self):
        """List calendars with visual widget."""
        result = ToolResult()
        widget = CalendarsListWidget()
        result.set_widget(widget)
        
        def fetch():
            client, error = self._get_client()
            if error:
                GLib.idle_add(widget.set_error, error)
                result.set_output(error)
                return
            
            try:
                calendars, err = client.list_calendars_raw()
                if err:
                    GLib.idle_add(widget.set_error, err)
                    result.set_output(err)
                else:
                    GLib.idle_add(widget.set_calendars, calendars)
                    output = client.list_calendars()
                    result.set_output(output)
            except Exception as e:
                GLib.idle_add(widget.set_error, str(e))
                result.set_output(f"Error: {str(e)}")
        
        thread = threading.Thread(target=fetch)
        thread.start()
        return result

    def nc_list_calendars_restore(self, tool_uuid: str):
        """Restore calendars list widget."""
        result = ToolResult()
        widget = CalendarsListWidget()
        output = self.ui_controller.get_tool_result_by_id(tool_uuid)
        widget.set_loading(False)
        result.set_widget(widget)
        result.set_output(output)
        return result

    def nc_list_calendar_events_widget(self, calendar_name: str, start: str, end: str):
        """List calendar events with visual widget."""
        result = ToolResult()
        widget = CalendarEventsWidget(calendar_name)
        result.set_widget(widget)
        
        def fetch():
            client, error = self._get_client()
            if error:
                GLib.idle_add(widget.set_error, error)
                result.set_output(error)
                return
            
            try:
                events, err = client.list_calendar_events_raw(calendar_name, start, end)
                if err:
                    GLib.idle_add(widget.set_error, err)
                    result.set_output(err)
                else:
                    GLib.idle_add(widget.set_events, events)
                    output = client.list_calendar_events(calendar_name, start, end)
                    result.set_output(output)
            except Exception as e:
                GLib.idle_add(widget.set_error, str(e))
                result.set_output(f"Error: {str(e)}")
        
        thread = threading.Thread(target=fetch)
        thread.start()
        return result

    def nc_list_calendar_events_restore(self, tool_uuid: str, calendar_name: str, start: str, end: str):
        """Restore calendar events widget."""
        result = ToolResult()
        widget = CalendarEventsWidget(calendar_name)
        output = self.ui_controller.get_tool_result_by_id(tool_uuid)
        widget.set_loading(False)
        result.set_widget(widget)
        result.set_output(output)
        return result

    def nc_list_addressbooks_widget(self):
        """List address books with visual widget."""
        result = ToolResult()
        widget = AddressBooksWidget()
        result.set_widget(widget)
        
        def fetch():
            client, error = self._get_client()
            if error:
                GLib.idle_add(widget.set_error, error)
                result.set_output(error)
                return
            
            try:
                books, err = client.list_addressbooks_raw()
                if err:
                    GLib.idle_add(widget.set_error, err)
                    result.set_output(err)
                else:
                    GLib.idle_add(widget.set_addressbooks, books)
                    output = client.list_addressbooks()
                    result.set_output(output)
            except Exception as e:
                GLib.idle_add(widget.set_error, str(e))
                result.set_output(f"Error: {str(e)}")
        
        thread = threading.Thread(target=fetch)
        thread.start()
        return result

    def nc_list_addressbooks_restore(self, tool_uuid: str):
        """Restore address books widget."""
        result = ToolResult()
        widget = AddressBooksWidget()
        output = self.ui_controller.get_tool_result_by_id(tool_uuid)
        widget.set_loading(False)
        result.set_widget(widget)
        result.set_output(output)
        return result

    def nc_list_contacts_widget(self, addressbook_name: str, page: int = 1, search_term: str = ""):
        """List contacts with visual widget."""
        result = ToolResult()
        # Initial widget with minimal info, updated later
        widget = ContactsWidget(addressbook_name, page=page)
        result.set_widget(widget)
        
        def fetch():
            client, error = self._get_client()
            if error:
                GLib.idle_add(widget.set_error, error)
                result.set_output(error)
                return
            
            try:
                res_dict, err = client.list_contacts_raw(addressbook_name, page, 30, search_term)
                if err:
                    GLib.idle_add(widget.set_error, err)
                    result.set_output(err)
                else:
                    contacts = res_dict['contacts']
                    total = res_dict['total']
                    total_pages = (total + 29) // 30 if total else 1
                    
                    # Update widget subtitle with correct page count
                    def update_ui():
                        widget.subtitle_label.set_label(f"{addressbook_name} (Page {page}/{total_pages})")
                        widget.set_contacts(contacts)
                        
                    GLib.idle_add(update_ui)
                    
                    output = client.list_contacts(addressbook_name, page, 30, search_term)
                    result.set_output(output)
            except Exception as e:
                GLib.idle_add(widget.set_error, str(e))
                result.set_output(f"Error: {str(e)}")
        
        thread = threading.Thread(target=fetch)
        thread.start()
        return result

    def nc_list_contacts_restore(self, tool_uuid: str, addressbook_name: str, page: int = 1, search_term: str = ""):
        """Restore contacts widget."""
        result = ToolResult()
        widget = ContactsWidget(addressbook_name, page=page)
        output = self.ui_controller.get_tool_result_by_id(tool_uuid)
        widget.set_loading(False)
        result.set_widget(widget)
        result.set_output(output)
        return result

    def nc_get_contact_widget(self, addressbook_name: str, contact_filename: str):
        """Get contact details with visual widget."""
        result = ToolResult()
        widget = ContactDetailWidget()
        result.set_widget(widget)
        
        def fetch():
            client, error = self._get_client()
            if error:
                GLib.idle_add(widget.set_error, error)
                result.set_output(error)
                return
            
            try:
                data, err = client.get_contact_raw(addressbook_name, contact_filename)
                if err:
                    GLib.idle_add(widget.set_error, err)
                    result.set_output(err)
                else:
                    GLib.idle_add(widget.set_details, data)
                    output = client.get_contact(addressbook_name, contact_filename)
                    result.set_output(output)
            except Exception as e:
                GLib.idle_add(widget.set_error, str(e))
                result.set_output(f"Error: {str(e)}")
        
        thread = threading.Thread(target=fetch)
        thread.start()
        return result

    def nc_get_contact_restore(self, tool_uuid: str, addressbook_name: str, contact_filename: str):
        """Restore contact detail widget."""
        result = ToolResult()
        widget = ContactDetailWidget()
        output = self.ui_controller.get_tool_result_by_id(tool_uuid)
        widget.set_loading(False)
        result.set_widget(widget)
        result.set_output(output)
        return result

    def nc_list_deck_boards_widget(self):
        """List Deck boards with visual widget."""
        result = ToolResult()
        widget = DeckBoardWidget()
        result.set_widget(widget)
        
        def fetch():
            client, error = self._get_client()
            if error:
                GLib.idle_add(widget.set_error, error)
                result.set_output(error)
                return
            
            try:
                boards, err = client.list_deck_boards_raw()
                if err:
                    GLib.idle_add(widget.set_error, err)
                    result.set_output(err)
                else:
                    GLib.idle_add(widget.set_boards, boards)
                    output = client.list_deck_boards()
                    result.set_output(output)
            except Exception as e:
                GLib.idle_add(widget.set_error, str(e))
                result.set_output(f"Error: {str(e)}")
        
        thread = threading.Thread(target=fetch)
        thread.start()
        return result

    def nc_list_deck_boards_restore(self, tool_uuid: str):
        """Restore Deck boards widget."""
        result = ToolResult()
        widget = DeckBoardWidget()
        output = self.ui_controller.get_tool_result_by_id(tool_uuid)
        widget.set_loading(False)
        result.set_widget(widget)
        result.set_output(output)
        return result

    def nc_list_deck_stacks_widget(self, board_id: int):
        """List Deck stacks with visual widget."""
        result = ToolResult()
        widget = DeckStacksWidget(board_id)
        result.set_widget(widget)
        
        def fetch():
            client, error = self._get_client()
            if error:
                GLib.idle_add(widget.set_error, error)
                result.set_output(error)
                return
            
            try:
                stacks, err = client.list_deck_stacks_raw(board_id)
                if err:
                    GLib.idle_add(widget.set_error, err)
                    result.set_output(err)
                else:
                    GLib.idle_add(widget.set_stacks, stacks)
                    output = client.list_deck_stacks(board_id)
                    result.set_output(output)
            except Exception as e:
                GLib.idle_add(widget.set_error, str(e))
                result.set_output(f"Error: {str(e)}")
        
        thread = threading.Thread(target=fetch)
        thread.start()
        return result

    def nc_list_deck_stacks_restore(self, tool_uuid: str, board_id: int):
        """Restore Deck stacks widget."""
        result = ToolResult()
        widget = DeckStacksWidget(board_id)
        output = self.ui_controller.get_tool_result_by_id(tool_uuid)
        widget.set_loading(False)
        result.set_widget(widget)
        result.set_output(output)
        return result

    def nc_list_deck_cards_widget(self, board_id: int, stack_id: int):
        """List Deck cards with visual widget."""
        result = ToolResult()
        widget = DeckCardsWidget(board_id, stack_id)
        result.set_widget(widget)
        
        def fetch():
            client, error = self._get_client()
            if error:
                GLib.idle_add(widget.set_error, error)
                result.set_output(error)
                return
            
            try:
                cards, err = client.list_deck_cards_raw(board_id, stack_id)
                if err:
                    GLib.idle_add(widget.set_error, err)
                    result.set_output(err)
                else:
                    GLib.idle_add(widget.set_cards, cards)
                    output = client.list_deck_cards(board_id, stack_id)
                    result.set_output(output)
            except Exception as e:
                GLib.idle_add(widget.set_error, str(e))
                result.set_output(f"Error: {str(e)}")
        
        thread = threading.Thread(target=fetch)
        thread.start()
        return result

    def nc_list_deck_cards_restore(self, tool_uuid: str, board_id: int, stack_id: int):
        """Restore Deck cards widget."""
        result = ToolResult()
        widget = DeckCardsWidget(board_id, stack_id)
        output = self.ui_controller.get_tool_result_by_id(tool_uuid)
        widget.set_loading(False)
        result.set_widget(widget)
        result.set_output(output)
        return result

    def nc_list_recipes_widget(self):
        """List recipes with visual widget."""
        result = ToolResult()
        widget = RecipesListWidget()
        result.set_widget(widget)
        
        def fetch():
            client, error = self._get_client()
            if error:
                GLib.idle_add(widget.set_error, error)
                result.set_output(error)
                return
            
            try:
                recipes, err = client.list_recipes_raw()
                if err:
                    GLib.idle_add(widget.set_error, err)
                    result.set_output(err)
                else:
                    GLib.idle_add(widget.set_recipes, recipes)
                    output = client.list_recipes()
                    result.set_output(output)
            except Exception as e:
                GLib.idle_add(widget.set_error, str(e))
                result.set_output(f"Error: {str(e)}")
        
        thread = threading.Thread(target=fetch)
        thread.start()
        return result

    def nc_list_recipes_restore(self, tool_uuid: str):
        """Restore recipes list widget."""
        result = ToolResult()
        widget = RecipesListWidget()
        output = self.ui_controller.get_tool_result_by_id(tool_uuid)
        widget.set_loading(False)
        result.set_widget(widget)
        result.set_output(output)
        return result

    def nc_get_recipe_widget(self, recipe_id: int):
        """Get recipe with visual widget."""
        result = ToolResult()
        widget = RecipeWidget()
        result.set_widget(widget)
        
        def fetch():
            client, error = self._get_client()
            if error:
                GLib.idle_add(widget.set_error, error)
                result.set_output(error)
                return
            
            try:
                recipe, err = client.get_recipe_raw(recipe_id)
                if err:
                    GLib.idle_add(widget.set_error, err)
                    result.set_output(err)
                else:
                    GLib.idle_add(widget.set_recipe, 
                        recipe.get('name', ''),
                        recipe.get('description', ''),
                        recipe.get('ingredients', ''))
                    output = client.get_recipe(recipe_id)
                    result.set_output(output)
            except Exception as e:
                GLib.idle_add(widget.set_error, str(e))
                result.set_output(f"Error: {str(e)}")
        
        thread = threading.Thread(target=fetch)
        thread.start()
        return result

    def nc_get_recipe_restore(self, tool_uuid: str, recipe_id: int):
        """Restore recipe widget."""
        result = ToolResult()
        widget = RecipeWidget()
        output = self.ui_controller.get_tool_result_by_id(tool_uuid)
        widget.set_loading(False)
        result.set_widget(widget)
        result.set_output(output)
        return result

    # ========== Simple tools (no widgets) ==========

    def nc_read_file(self, path: str):
        """Read the content of a file from Nextcloud."""
        client, error = self._get_client()
        if error: return error
        return client.read_file(path)

    def nc_write_file(self, path: str, content: str):
        """Write content to a file in Nextcloud. Creates or overwrites."""
        client, error = self._get_client()
        if error: return error
        return client.write_file(path, content)

    def nc_delete_file(self, path: str):
        """Delete a file or directory in Nextcloud."""
        client, error = self._get_client()
        if error: return error
        return client.delete_file(path)

    def nc_create_directory(self, path: str):
        """Create a new directory in Nextcloud."""
        client, error = self._get_client()
        if error: return error
        return client.create_directory(path)

    def nc_create_note(self, title: str, content: str, category: str = ""):
        """Create a new note in Nextcloud."""
        client, error = self._get_client()
        if error: return error
        return client.create_note(title, content, category)

    def nc_delete_note(self, note_id: int):
        """Delete a note from Nextcloud."""
        client, error = self._get_client()
        if error: return error
        return client.delete_note(note_id)

    def nc_create_calendar_event(self, calendar_name: str, title: str, start_dt: str, end_dt: str, description: str = ""):
        """Create a new event in a calendar. Timestamps should be in format YYYYMMDDTHHMMSSZ (e.g. 20231027T100000Z)."""
        client, error = self._get_client()
        if error: return error
        return client.create_calendar_event(calendar_name, title, start_dt, end_dt, description)

    def nc_get_calendar_event(self, calendar_name: str, event_filename: str):
        """Get the full ICS content of a calendar event."""
        client, error = self._get_client()
        if error: return error
        return client.get_calendar_event(calendar_name, event_filename)

    def nc_delete_calendar_event(self, calendar_name: str, event_filename: str):
        """Delete a calendar event (requires .ics filename resource)."""
        client, error = self._get_client()
        if error: return error
        return client.delete_calendar_event(calendar_name, event_filename)

    def nc_create_deck_board(self, title: str, color: str = "000000"):
        """Create a new Deck board. Color is a hex string without #."""
        client, error = self._get_client()
        if error: return error
        return client.create_deck_board(title, color)

    def nc_create_deck_stack(self, board_id: int, title: str, order: int = 0):
        """Create a new stack in a Deck board."""
        client, error = self._get_client()
        if error: return error
        return client.create_deck_stack(board_id, title, order)

    def nc_update_deck_stack(self, board_id: int, stack_id: int, title: str = None, order: int = None):
        """Update a stack in a Deck board."""
        client, error = self._get_client()
        if error: return error
        return client.update_deck_stack(board_id, stack_id, title, order)

    def nc_delete_deck_stack(self, board_id: int, stack_id: int):
        """Delete a stack from a Deck board."""
        client, error = self._get_client()
        if error: return error
        return client.delete_deck_stack(board_id, stack_id)

    def nc_create_deck_card(self, board_id: int, stack_id: int, title: str, description: str = "", ctype: str = "plain", order: int = 0, duedate: str = None):
        """Create a new card in a stack. duedate in ISO format."""
        client, error = self._get_client()
        if error: return error
        return client.create_deck_card(board_id, stack_id, title, description, ctype, order, duedate)

    def nc_update_deck_card(self, board_id: int, stack_id: int, card_id: int, title: str = None, description: str = None, order: int = None, duedate: str = None, archived: bool = None):
        """Update a card. Set archived to true/false to archive/unarchive."""
        client, error = self._get_client()
        if error: return error
        return client.update_deck_card(board_id, stack_id, card_id, title, description, order, duedate, archived)

    def nc_reorder_deck_card(self, board_id: int, stack_id: int, card_id: int, order: int, target_stack_id: int = None):
        """Reorder a card within a stack or move it to another stack."""
        client, error = self._get_client()
        if error: return error
        return client.reorder_deck_card(board_id, stack_id, card_id, order, target_stack_id)

    def nc_delete_deck_card(self, board_id: int, stack_id: int, card_id: int):
        """Delete a card."""
        client, error = self._get_client()
        if error: return error
        return client.delete_deck_card(board_id, stack_id, card_id)

    def nc_archive_deck_card(self, board_id: int, stack_id: int, card_id: int):
        """Archive a card."""
        client, error = self._get_client()
        if error: return error
        return client.update_deck_card(board_id, stack_id, card_id, archived=True)

    def nc_unarchive_deck_card(self, board_id: int, stack_id: int, card_id: int):
        """Unarchive a card."""
        client, error = self._get_client()
        if error: return error
        return client.update_deck_card(board_id, stack_id, card_id, archived=False)

    def nc_create_deck_label(self, board_id: int, title: str, color: str):
        """Create a new label in a board. Color is hex without #."""
        client, error = self._get_client()
        if error: return error
        return client.create_deck_label(board_id, title, color)

    def nc_update_deck_label(self, board_id: int, label_id: int, title: str = None, color: str = None):
        """Update a label."""
        client, error = self._get_client()
        if error: return error
        return client.update_deck_label(board_id, label_id, title, color)

    def nc_delete_deck_label(self, board_id: int, label_id: int):
        """Delete a label."""
        client, error = self._get_client()
        if error: return error
        return client.delete_deck_label(board_id, label_id)

    def nc_assign_deck_label_to_card(self, board_id: int, stack_id: int, card_id: int, label_id: int):
        """Assign a label to a card."""
        client, error = self._get_client()
        if error: return error
        return client.assign_deck_label(board_id, stack_id, card_id, label_id)

    def nc_remove_deck_label_from_card(self, board_id: int, stack_id: int, card_id: int, label_id: int):
        """Remove a label from a card."""
        client, error = self._get_client()
        if error: return error
        return client.remove_deck_label(board_id, stack_id, card_id, label_id)

    def nc_assign_deck_user_to_card(self, board_id: int, stack_id: int, card_id: int, user_id: str):
        """Assign a user to a card."""
        client, error = self._get_client()
        if error: return error
        return client.assign_deck_user(board_id, stack_id, card_id, user_id)

    def nc_remove_deck_user_from_card(self, board_id: int, stack_id: int, card_id: int, user_id: str):
        """Remove a user from a card."""
        client, error = self._get_client()
        if error: return error
        return client.remove_deck_user(board_id, stack_id, card_id, user_id)

    def nc_create_recipe(self, name: str, description: str = "", ingredients: str = "", instructions: str = ""):
        """Create a new recipe in Nextcloud Cookbook."""
        client, error = self._get_client()
        if error: return error
        return client.create_recipe(name, description, ingredients, instructions)

    def nc_import_recipe(self, url: str):
        """Import a recipe from a URL into Nextcloud Cookbook."""
        client, error = self._get_client()
        if error: return error
        return client.import_recipe(url)

    def get_tools(self):
        return [
            # Files - with widgets
            Tool("nc_list_files", "List files and directories in Nextcloud. Path is relative to user root.", 
                 self.nc_list_files_widget, restore_func=self.nc_list_files_restore, tools_group="Files"),
            create_io_tool("nc_read_file", "Read file content from Nextcloud.", self.nc_read_file, tools_group="Files"),
            create_io_tool("nc_write_file", "Write content to a file in Nextcloud.", self.nc_write_file, tools_group="Files"),
            create_io_tool("nc_delete_file", "Delete a file or directory in Nextcloud.", self.nc_delete_file, tools_group="Files"),
            create_io_tool("nc_create_directory", "Create a directory in Nextcloud.", self.nc_create_directory, tools_group="Files"),
            
            # Notes - with widgets
            Tool("nc_list_notes", "List all notes.", 
                 self.nc_list_notes_widget, restore_func=self.nc_list_notes_restore, tools_group="Notes"),
            Tool("nc_get_note", "Get content of a note by ID.", 
                 self.nc_get_note_widget, restore_func=self.nc_get_note_restore, tools_group="Notes"),
            create_io_tool("nc_create_note", "Create a new note.", self.nc_create_note, tools_group="Notes"),
            create_io_tool("nc_delete_note", "Delete a note by ID.", self.nc_delete_note, tools_group="Notes"),

            # Calendar - with widgets
            Tool("nc_list_calendars", "List all calendars.", 
                 self.nc_list_calendars_widget, restore_func=self.nc_list_calendars_restore, tools_group="Calendar"),
            create_io_tool("nc_create_calendar_event", "Create a new calendar event. Timestamps: YYYYMMDDTHHMMSSZ.", self.nc_create_calendar_event, tools_group="Calendar"),
            Tool("nc_list_calendar_events", "List events in a calendar within a time range.", 
                 self.nc_list_calendar_events_widget, restore_func=self.nc_list_calendar_events_restore, tools_group="Calendar"),
            create_io_tool("nc_get_calendar_event", "Get details (ICS) of a calendar event.", self.nc_get_calendar_event, tools_group="Calendar"),
            create_io_tool("nc_delete_calendar_event", "Delete a calendar event.", self.nc_delete_calendar_event, tools_group="Calendar"),

            # Contacts - with widgets
            Tool("nc_list_addressbooks", "List address books.", 
                 self.nc_list_addressbooks_widget, restore_func=self.nc_list_addressbooks_restore, tools_group="Contacts"),
            Tool("nc_list_contacts", "List contacts in an address book with paging (30 per page) and search.", 
                 self.nc_list_contacts_widget, restore_func=self.nc_list_contacts_restore, tools_group="Contacts"),
            Tool("nc_get_contact", "Get details of a specific contact.", 
                 self.nc_get_contact_widget, restore_func=self.nc_get_contact_restore, tools_group="Contacts"),

            # Deck - with widgets
            Tool("nc_list_deck_boards", "List all Deck boards.", 
                 self.nc_list_deck_boards_widget, restore_func=self.nc_list_deck_boards_restore, tools_group="Deck"),
            create_io_tool("nc_create_deck_board", "Create a new Deck board.", self.nc_create_deck_board, tools_group="Deck"),
            Tool("nc_list_deck_stacks", "List stacks in a board.", 
                 self.nc_list_deck_stacks_widget, restore_func=self.nc_list_deck_stacks_restore, tools_group="Deck"),
            Tool("nc_list_deck_cards", "List cards in a stack.", 
                 self.nc_list_deck_cards_widget, restore_func=self.nc_list_deck_cards_restore, tools_group="Deck"),
            
            create_io_tool("nc_create_deck_stack", "Create a new stack.", self.nc_create_deck_stack, tools_group="Deck"),
            create_io_tool("nc_update_deck_stack", "Update a stack.", self.nc_update_deck_stack, tools_group="Deck"),
            create_io_tool("nc_delete_deck_stack", "Delete a stack.", self.nc_delete_deck_stack, tools_group="Deck"),
            create_io_tool("nc_create_deck_card", "Create a new card.", self.nc_create_deck_card, tools_group="Deck"),
            create_io_tool("nc_update_deck_card", "Update a card.", self.nc_update_deck_card, tools_group="Deck"),
            create_io_tool("nc_archive_deck_card", "Archive a card.", self.nc_archive_deck_card, tools_group="Deck"),
            create_io_tool("nc_unarchive_deck_card", "Unarchive a card.", self.nc_unarchive_deck_card, tools_group="Deck"),
            create_io_tool("nc_reorder_deck_card", "Reorder or move a card.", self.nc_reorder_deck_card, tools_group="Deck"),
            create_io_tool("nc_delete_deck_card", "Delete a card.", self.nc_delete_deck_card, tools_group="Deck"),
            create_io_tool("nc_create_deck_label", "Create a new label.", self.nc_create_deck_label, tools_group="Deck"),
            create_io_tool("nc_update_deck_label", "Update a label.", self.nc_update_deck_label, tools_group="Deck"),
            create_io_tool("nc_delete_deck_label", "Delete a label.", self.nc_delete_deck_label, tools_group="Deck"),
            create_io_tool("nc_assign_deck_label_to_card", "Assign a label to a card.", self.nc_assign_deck_label_to_card, tools_group="Deck"),
            create_io_tool("nc_remove_deck_label_from_card", "Remove a label from a card.", self.nc_remove_deck_label_from_card, tools_group="Deck"),
            create_io_tool("nc_assign_deck_user_to_card", "Assign a user to a card.", self.nc_assign_deck_user_to_card, tools_group="Deck"),
            create_io_tool("nc_remove_deck_user_from_card", "Remove a user from a card.", self.nc_remove_deck_user_from_card, tools_group="Deck"),

            # Cookbook - with widgets
            Tool("nc_list_recipes", "List cookbook recipes.", 
                 self.nc_list_recipes_widget, restore_func=self.nc_list_recipes_restore, tools_group="Cookbook"),
            Tool("nc_get_recipe", "Get details of a recipe.", 
                 self.nc_get_recipe_widget, restore_func=self.nc_get_recipe_restore, tools_group="Cookbook"),
            create_io_tool("nc_create_recipe", "Create a new recipe manually.", self.nc_create_recipe, tools_group="Cookbook"),
            create_io_tool("nc_import_recipe", "Import a recipe from a URL.", self.nc_import_recipe, tools_group="Cookbook"),
        ]