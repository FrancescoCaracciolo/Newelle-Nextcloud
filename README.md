# Newelle-Nextcloud
Interact with your nextcloud instance using Newelle.

<img width="1524" height="837" alt="Frame 70" src="https://github.com/user-attachments/assets/ad0cbce6-5a2c-4a00-b76c-a0e9881287e7" />

# Nextcloud Extension Tools

## Files

- **nc_list_files** - List files and directories in Nextcloud. Path is relative to user root.
- **nc_read_file** - Read file content from Nextcloud.
- **nc_write_file** - Write content to a file in Nextcloud.
- **nc_delete_file** - Delete a file or directory in Nextcloud.
- **nc_create_directory** - Create a directory in Nextcloud.

## Notes

- **nc_list_notes** - List all notes.
- **nc_get_note** - Get content of a note by ID.
- **nc_create_note** - Create a new note.
- **nc_delete_note** - Delete a note by ID.

## Calendar

- **nc_list_calendars** - List all calendars.
- **nc_create_calendar_event** - Create a new calendar event. Timestamps: YYYYMMDDTHHMMSSZ.
- **nc_list_calendar_events** - List events in a calendar within a time range.
- **nc_get_calendar_event** - Get details (ICS) of a calendar event.
- **nc_delete_calendar_event** - Delete a calendar event.

## Contacts

- **nc_list_addressbooks** - List address books.
- **nc_list_contacts** - List contacts in an address book with paging (30 per page) and search.
- **nc_get_contact** - Get details of a specific contact.

## Deck

- **nc_list_deck_boards** - List all Deck boards.
- **nc_create_deck_board** - Create a new Deck board.
- **nc_list_deck_stacks** - List stacks in a board.
- **nc_list_deck_cards** - List cards in a stack.
- **nc_create_deck_stack** - Create a new stack.
- **nc_update_deck_stack** - Update a stack.
- **nc_delete_deck_stack** - Delete a stack.
- **nc_create_deck_card** - Create a new card.
- **nc_update_deck_card** - Update a card.
- **nc_archive_deck_card** - Archive a card.
- **nc_unarchive_deck_card** - Unarchive a card.
- **nc_reorder_deck_card** - Reorder or move a card.
- **nc_delete_deck_card** - Delete a card.
- **nc_create_deck_label** - Create a new label.
- **nc_update_deck_label** - Update a label.
- **nc_delete_deck_label** - Delete a label.
- **nc_assign_deck_label_to_card** - Assign a label to a card.
- **nc_remove_deck_label_from_card** - Remove a label from a card.
- **nc_assign_deck_user_to_card** - Assign a user to a card.
- **nc_remove_deck_user_from_card** - Remove a user from a card.

## Cookbook

- **nc_list_recipes** - List cookbook recipes.
- **nc_get_recipe** - Get details of a recipe.
- **nc_create_recipe** - Create a new recipe manually.
- **nc_import_recipe** - Import a recipe from a URL.
