# Text Search WordPress Plugin

This plugin allows users to search through extracted text from images stored in the PostgreSQL database.

## Features

- Search extracted text content from uploaded images
- Real-time AJAX search with highlighting
- Responsive search interface
- Admin panel with connection status
- Shortcode integration for easy placement

## Installation

1. The plugin is automatically mounted to WordPress via Docker Compose
2. In WordPress admin, go to Plugins and activate "Text Search"

## Usage

### Adding Search to Pages/Posts

Add the shortcode `[text_search]` to any page or post where you want the search functionality to appear.

Optional parameters:
- `placeholder`: Custom placeholder text for the search input

Example:
```
[text_search placeholder="Search extracted text..."]
```

### Admin Settings

Go to **Settings > Text Search** in WordPress admin to:
- Check database connection status
- View total number of extracted text records
- See usage instructions

## Features

- **Real-time search**: Uses AJAX for fast searching without page reloads
- **Text highlighting**: Search terms are highlighted in results
- **Pagination**: Results are limited to 50 for performance
- **Security**: Uses WordPress nonces for AJAX security
- **Error handling**: Graceful error handling and user feedback

## Technical Details

- Connects to PostgreSQL database running in Docker
- Searches the `extracted_text` table with `ILIKE` for case-insensitive matching
- Joins with `images` table to show filename information
- Truncates long text content to 500 characters for display

## Database Schema

The plugin expects these PostgreSQL tables:
- `images`: Contains image metadata
- `extracted_text`: Contains OCR/extracted text linked to images

## Troubleshooting

1. **Plugin not working**: Check that PostgreSQL service is running
2. **No search results**: Verify that images have been processed and text extracted
3. **Connection issues**: Check database credentials in the plugin code