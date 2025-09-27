<?php
/**
 * Plugin Name: Text Search
 * Description: Search extracted text from images via Flask API
 * Version: 1.0
 * Author: Your Name
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

class TextSearchPlugin {

    private $api_base_url = 'http://flask-app:5000'; // Docker service name

    public function __construct() {
        add_action('wp_enqueue_scripts', array($this, 'enqueue_scripts'));
        add_shortcode('text_search', array($this, 'text_search_shortcode'));
        add_action('wp_ajax_search_text', array($this, 'ajax_search_text'));
        add_action('wp_ajax_nopriv_search_text', array($this, 'ajax_search_text'));
    }

    public function enqueue_scripts() {
        wp_enqueue_script('jquery');

        // Add CSS styles
        wp_add_inline_style('wp-block-library', '
            .text-search-container {
                max-width: 800px;
                margin: 20px auto;
                padding: 20px;
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: #fff;
            }
            .search-form {
                margin-bottom: 20px;
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
            }
            .text-search-input {
                flex: 1;
                min-width: 300px;
                padding: 12px;
                font-size: 16px;
                border: 2px solid #ddd;
                border-radius: 4px;
                outline: none;
                transition: border-color 0.3s;
            }
            .text-search-input:focus {
                border-color: #0073aa;
            }
            .text-search-button {
                padding: 12px 24px;
                font-size: 16px;
                background-color: #0073aa;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                transition: background-color 0.3s;
            }
            .text-search-button:hover {
                background-color: #005a87;
            }
            .text-search-button:disabled {
                background-color: #ccc;
                cursor: not-allowed;
            }
            .search-results {
                margin-top: 20px;
            }
            .search-results h3 {
                color: #333;
                border-bottom: 2px solid #0073aa;
                padding-bottom: 10px;
            }
            .search-result-item {
                padding: 20px;
                margin: 15px 0;
                border: 1px solid #eee;
                border-radius: 6px;
                background-color: #f9f9f9;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .search-result-filename {
                font-weight: bold;
                color: #0073aa;
                margin-bottom: 10px;
                font-size: 18px;
            }
            .search-result-text {
                line-height: 1.6;
                color: #333;
            }
            .search-highlight {
                background-color: #ffff00;
                font-weight: bold;
                padding: 2px 4px;
                border-radius: 2px;
            }
            .loading {
                text-align: center;
                padding: 40px 20px;
                color: #666;
                font-style: italic;
            }
            .no-results {
                text-align: center;
                padding: 40px 20px;
                color: #666;
                background-color: #f0f0f0;
                border-radius: 4px;
            }
            .error {
                text-align: center;
                padding: 20px;
                color: #d63638;
                background-color: #ffeaea;
                border: 1px solid #d63638;
                border-radius: 4px;
            }
            .search-stats {
                margin: 10px 0;
                font-size: 14px;
                color: #666;
            }
        ');
    }

    public function text_search_shortcode($atts) {
        $atts = shortcode_atts(array(
            'placeholder' => 'Enter text to search...'
        ), $atts);

        // Generate unique IDs to avoid conflicts
        $unique_id = uniqid('text_search_');

        ob_start();
        ?>
        <div class="text-search-container">
            <div class="search-form">
                <input type="text" id="<?php echo $unique_id; ?>_input" class="text-search-input" placeholder="<?php echo esc_attr($atts['placeholder']); ?>" />
                <button id="<?php echo $unique_id; ?>_submit" class="text-search-button">Search</button>
            </div>
            <div id="<?php echo $unique_id; ?>_results" class="search-results"></div>
        </div>

        <script>
        jQuery(document).ready(function($) {
            const uniqueId = '<?php echo $unique_id; ?>';
            const $input = $('#' + uniqueId + '_input');
            const $button = $('#' + uniqueId + '_submit');
            const $results = $('#' + uniqueId + '_results');

            $button.click(function() {
                performSearch();
            });

            $input.keypress(function(e) {
                if (e.which == 13) {
                    performSearch();
                }
            });

            function performSearch() {
                const searchTerm = $input.val().trim();
                if (searchTerm === '') {
                    alert('Please enter a search term');
                    return;
                }

                $button.prop('disabled', true).text('Searching...');
                $results.html('<div class="loading">🔍 Searching through extracted text...</div>');

                $.ajax({
                    url: '<?php echo admin_url('admin-ajax.php'); ?>',
                    type: 'POST',
                    data: {
                        action: 'search_text',
                        search_term: searchTerm,
                        nonce: '<?php echo wp_create_nonce('text_search_nonce'); ?>'
                    },
                    success: function(response) {
                        $button.prop('disabled', false).text('Search');

                        if (response.success) {
                            displayResults(response.data.results, searchTerm, response.data.count);
                        } else {
                            $results.html('<div class="error">Error: ' + (response.data.message || 'Unknown error occurred') + '</div>');
                        }
                    },
                    error: function(xhr, status, error) {
                        $button.prop('disabled', false).text('Search');
                        $results.html('<div class="error">Network error occurred. Please try again.</div>');
                        console.error('Search error:', error);
                    }
                });
            }

            function displayResults(results, searchTerm, count) {
                if (!results || results.length === 0) {
                    $results.html('<div class="no-results">No results found for "' + searchTerm + '"<br><small>Try different keywords or check spelling</small></div>');
                    return;
                }

                let html = '<h3>Search Results</h3>';
                html += '<div class="search-stats">Found ' + count + ' result' + (count !== 1 ? 's' : '') + ' for "' + searchTerm + '"</div>';

                results.forEach(function(result) {
                    const highlightedText = highlightSearchTerm(result.text_content, searchTerm);
                    html += '<div class="search-result-item">';
                    html += '<div class="search-result-filename">📄 ' + result.filename + '</div>';
                    html += '<div class="search-result-text">' + highlightedText + '</div>';
                    html += '</div>';
                });

                $results.html(html);
            }

            function highlightSearchTerm(text, searchTerm) {
                if (!text || !searchTerm) return text;

                const regex = new RegExp('(' + searchTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi');
                return text.replace(regex, '<span class="search-highlight">$1</span>');
            }
        });
        </script>
        <?php
        return ob_get_clean();
    }

    public function ajax_search_text() {
        // Verify nonce
        if (!wp_verify_nonce($_POST['nonce'], 'text_search_nonce')) {
            wp_send_json_error(array('message' => 'Security check failed'));
            return;
        }

        $search_term = sanitize_text_field($_POST['search_term']);

        if (empty($search_term)) {
            wp_send_json_error(array('message' => 'Search term is required'));
            return;
        }

        try {
            // Make request to Flask API
            $api_url = $this->api_base_url . '/api/search?q=' . urlencode($search_term);

            $response = wp_remote_get($api_url, array(
                'timeout' => 30,
                'headers' => array(
                    'Accept' => 'application/json'
                )
            ));

            if (is_wp_error($response)) {
                wp_send_json_error(array('message' => 'Failed to connect to search service: ' . $response->get_error_message()));
                return;
            }

            $response_code = wp_remote_retrieve_response_code($response);
            $response_body = wp_remote_retrieve_body($response);

            if ($response_code !== 200) {
                wp_send_json_error(array('message' => 'Search service returned error: ' . $response_code));
                return;
            }

            $data = json_decode($response_body, true);

            if (json_last_error() !== JSON_ERROR_NONE) {
                wp_send_json_error(array('message' => 'Invalid response from search service'));
                return;
            }

            if (isset($data['error'])) {
                wp_send_json_error(array('message' => $data['error']));
                return;
            }

            wp_send_json_success(array(
                'results' => $data['results'] ?? array(),
                'count' => $data['count'] ?? 0
            ));

        } catch (Exception $e) {
            wp_send_json_error(array('message' => 'Search failed: ' . $e->getMessage()));
        }
    }

    private function test_api_connection() {
        $response = wp_remote_get($this->api_base_url . '/api/search?q=test', array(
            'timeout' => 10
        ));

        return !is_wp_error($response) && wp_remote_retrieve_response_code($response) !== false;
    }
}

// Initialize the plugin
new TextSearchPlugin();

// Add admin menu for plugin settings
add_action('admin_menu', 'text_search_admin_menu');

function text_search_admin_menu() {
    add_options_page(
        'Text Search Settings',
        'Text Search',
        'manage_options',
        'text-search-settings',
        'text_search_admin_page'
    );
}

function text_search_admin_page() {
    $plugin = new TextSearchPlugin();
    ?>
    <div class="wrap">
        <h1>Text Search Plugin</h1>

        <div class="notice notice-info">
            <p><strong>How to use:</strong></p>
            <ul>
                <li>Add the shortcode <code>[text_search]</code> to any page or post to display the search form</li>
                <li>Users can search for text that has been extracted from uploaded images</li>
                <li>Results will show the filename and relevant text content with highlighted search terms</li>
                <li>The search connects to the Flask API running on port 5000</li>
            </ul>
        </div>

        <h2>API Connection Status</h2>
        <?php
        $api_url = 'http://flask-app:5000/api/search?q=test';
        $response = wp_remote_get($api_url, array('timeout' => 5));

        if (!is_wp_error($response) && wp_remote_retrieve_response_code($response) !== false) {
            $response_code = wp_remote_retrieve_response_code($response);
            if ($response_code == 200 || $response_code == 400) { // 400 is OK for empty query
                echo '<div class="notice notice-success"><p>✓ Successfully connected to Flask API</p></div>';

                // Try to get some stats
                $stats_response = wp_remote_get('http://flask-app:5000/', array('timeout' => 5));
                if (!is_wp_error($stats_response)) {
                    echo '<p>Flask application is running and accessible.</p>';
                }
            } else {
                echo '<div class="notice notice-warning"><p>⚠ API responded with status code: ' . $response_code . '</p></div>';
            }
        } else {
            echo '<div class="notice notice-error"><p>✗ Failed to connect to Flask API</p>';
            if (is_wp_error($response)) {
                echo '<p>Error: ' . $response->get_error_message() . '</p>';
            }
            echo '</div>';
        }
        ?>

        <h2>Shortcode Examples</h2>
        <table class="form-table">
            <tr>
                <th scope="row">Basic Search Form</th>
                <td><code>[text_search]</code></td>
            </tr>
            <tr>
                <th scope="row">Custom Placeholder</th>
                <td><code>[text_search placeholder="Search extracted text..."]</code></td>
            </tr>
        </table>
    </div>
    <?php
}