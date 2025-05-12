# Plan: Building a Mobile-Responsive Calendar View

## 1. Overview

The goal is to create a new HTML page (or a section within an existing one) in the FastAPI application, rendered using Jinja2 templates. This page will display a calendar-like grid:

-   **Columns**: Representing different stages.
-   **Rows**: Representing 15-minute time slots throughout the day.
-   **Cells**: Displaying events, which are clickable to show more details in a modal.
-   **Responsiveness**: The view must be usable and look good on both desktop and mobile devices.

The implementation will leverage the existing stack: FastAPI, Jinja2, SQLAlchemy for DB interaction, Tailwind CSS for styling, and vanilla JavaScript for interactivity. Data will be fetched directly from the database within the route handler and passed to the template.

## 2. Backend (Python - `app/main.py` and `app/crud.py`)

### a. New Route in `app/main.py`
-   Define a new route, e.g., `/calendar`, to serve the calendar page.
-   This route handler will:
    -   Accept an optional `selected_date` query parameter for filtering.
    -   Fetch all necessary data (stages, events for the selected date).
    -   Process data into a grid-friendly structure.
    -   Render the `calendar_view.html` template, passing the processed data.

    ```python
    # Conceptual structure in app/main.py
    # @app.get("/calendar", response_class=HTMLResponse)
    # async def read_calendar_view(
    #     request: Request,
    #     selected_date_str: Optional[str] = Query(None, alias="date"), # e.g., YYYY-MM-DD
    #     db: Session = Depends(get_db),
    #     current_user: models.User = Depends(get_current_active_user)
    # ):
    #     # 1. Determine target_date (from selected_date_str or default to today)
    #     # 2. Fetch stages: all_stages = crud.get_all_stages(db)
    #     # 3. Fetch events for target_date: relevant_events = crud.get_events_for_date(db, target_date)
    #     #    (Ensure events have artist and stage info eagerly loaded)
    #     # 4. Generate time_slots for the day (e.g., 08:00, 08:15, ... 23:45)
    #     # 5. Process events into events_by_stage_and_time (see Data Processing)
    #     # 6. Pass all_stages, time_slots, events_by_stage_and_time, relevant_events (for modal), etc., to template
    #     # return templates.TemplateResponse("calendar_view.html", { ... context ... })
    ```

### b. Data Fetching (`app/crud.py` or in route)
-   **Stages**: `crud.get_all_stages(db)`.
-   **Events**:
    -   Modify or create a CRUD function like `crud.get_events_for_date_range(db, start_datetime, end_datetime)` to fetch events within a specific day, ensuring `artist` and `stage` relationships are eagerly loaded (e.g., using `joinedload`).
-   **Time Slots**:
    -   Generate a list of 15-minute interval strings for the relevant day (e.g., "08:00", "08:15", ..., "23:45"). The range could be dynamic (based on first/last event of the day) or fixed.

### c. Data Processing for the Grid (in Route Handler)
-   Transform the list of fetched events into a nested dictionary structure for easy rendering:
    `events_by_stage_and_time = {stage_name: {time_slot_str: {"event_data": event_obj, "span": num_slots}}}`
-   Helper function `find_time_slot(datetime_obj, time_slots_list)`: Maps an event's start time to the corresponding 15-minute slot string.
-   Helper function `calculate_event_span(event_obj, slot_duration_minutes=15)`: Calculates how many 15-minute slots an event occupies.
-   **Crucial for rowspan**: Pre-calculate and mark cells that are "covered" by an event spanning multiple time slots.
    -   For an event spanning `N` slots, the main entry will be at its start slot with `span: N`.
    -   For the subsequent `N-1` slots in that stage's column, mark them as occupied (e.g., `events_by_stage_and_time[stage_name][subsequent_slot_str] = {"covered_by_event_id": event.id, "is_empty_placeholder": True }`). This simplifies Jinja logic.

## 3. Frontend (HTML - `app/templates/calendar_view.html`)

### a. Basic Structure
-   Extend `base.html`.
-   Include a date picker/filter form to allow users to select the day for the calendar.
-   Main content area for the calendar grid.

### b. Grid Layout (HTML Table)
-   The table will be wrapped in `<div class="overflow-x-auto">` for horizontal scrolling on mobile.
-   **Header Row**:
    -   First cell: "Time" (sticky).
    -   Subsequent cells: Stage names (from `all_stages`).
-   **Body Rows**:
    -   Iterate through `time_slots`. Each `time_slot` is a table row.
    -   First cell in each row: Time slot string (sticky).
    -   Subsequent cells: Iterate through `stages`.
        -   Lookup `event_info = events_by_stage_and_time[stage.name][time_slot]`.
        -   **If `event_info` exists and is not a "covered_by_event_id" placeholder**:
            -   Render a `<td>` with `rowspan="{{ event_info.span }}"`.
            -   Inside the `<td>`, a clickable `<div>` for the event, showing artist name and short time.
            -   `data-event-id="{{ event.event_id }}"` for JS interaction.
        -   **If `event_info` is a "covered_by_event_id" placeholder**:
            -   Do not render a `<td>` for this cell (it's spanned by a previous event).
        -   **Else (empty slot)**:
            -   Render an empty `<td>` to maintain grid structure.

### c. Event Modal
-   A hidden `<div>` for the modal, styled with Tailwind CSS.
-   Modal content (artist title, full times, stage, description, link to artist detail page, risk assessment info if available) will be populated by JavaScript.

### d. Mobile Responsiveness Specifics
-   **Horizontal Scrolling**: Achieved via `overflow-x-auto` on the table's wrapper.
-   **Sticky Time Column**: `position: sticky; left: 0;` for the first column (`<th>` and `<td>`) with appropriate `z-index` and background color to prevent content shining through during scroll.
-   **Font Sizes and Padding**: Use Tailwind's responsive prefixes (e.g., `text-xs sm:text-sm`, `p-1 md:p-2`) for cells and event content to optimize space on small screens.
-   **Modal Responsiveness**: Ensure the modal is centered, has a `max-width` for desktop, and scales down appropriately (e.g., `w-11/12`) on mobile. Content within the modal should be scrollable if it overflows.

## 4. JavaScript (Inline in `<script>` tag or `app/static/js/calendar.js`)

### a. Event Data
-   Pass the raw list of `relevant_events` (for the selected day) as a JSON string to JavaScript. This allows the modal to be populated without extra API calls.
    `const allEventsData = {{ relevant_events_for_modal | tojson | safe }};`

### b. Modal Interaction
-   `openEventModal(eventId)`:
    -   Finds the event data from `allEventsData` using `eventId`.
    -   Populates the modal's HTML content with event details.
    -   Shows the modal.
-   `closeEventModal()`: Hides the modal.
-   Event listeners on clickable event `<div>`s in the grid to trigger `openEventModal`.

### c. Date Filter
-   JavaScript to handle the date picker:
    -   On date change, reload the page with the new date as a query parameter (e.g., `window.location.href = '/calendar?date=' + newSelectedDate;`).
    -   Initialize the date picker with the `selected_date` from the URL query params, or default to today.

### d. Helper Functions
-   `formatDateTime(isoString, format)`: Client-side date formatting for display in the modal (can be basic or use a lightweight library if complex formatting is needed).

## 5. CSS (Tailwind CSS - via utility classes in HTML)

-   Style the table, cells, sticky column/header, event divs, and modal.
-   Ensure consistent cell heights for empty slots.
-   Use responsive prefixes (`sm:`, `md:`, `lg:`) extensively for adapting layout, typography, and spacing.
-   Example for event cell: `class="bg-blue-100 p-1 sm:p-1.5 rounded shadow hover:bg-blue-200 cursor-pointer h-full flex flex-col justify-between min-h-[60px]"` (min-height helps visual consistency).

## 6. Key Implementation Steps & Order

1.  **Backend Setup**:
    *   Create the new route in `main.py`.
    *   Implement/update CRUD functions for fetching stages and events by date range with eager loading.
    *   Implement the data processing logic (time slots, `events_by_stage_and_time` map, span calculation, "covered slot" marking).
2.  **Basic HTML Structure**:
    *   Create `calendar_view.html`.
    *   Implement the main table structure with loops for time slots and stages (initially without rowspan or event data, just to get the grid).
3.  **Populate Grid with Events**:
    *   Integrate the `events_by_stage_and_time` data into the table cells.
    *   Implement the `rowspan` logic based on the pre-processed "span" and "covered_by_event_id" flags. This is the most complex rendering part.
4.  **Modal Implementation**:
    *   Add HTML for the hidden modal.
    *   Write JavaScript to populate and toggle the modal, using the JSON data of events.
5.  **Styling and Basic Responsiveness**:
    *   Apply Tailwind CSS for basic table styling, cell appearance, and modal.
    *   Implement horizontal scrolling (`overflow-x-auto`) and sticky first column.
6.  **Date Filtering**:
    *   Add the date picker HTML.
    *   Add JavaScript to handle date changes and page reloads with the date query parameter.
    *   Ensure the backend route uses the `selected_date` parameter.
7.  **Mobile Responsiveness Refinements**:
    *   Test thoroughly on different screen sizes (using dev tools and physical devices).
    *   Adjust font sizes, padding, and element visibility using Tailwind's responsive prefixes (e.g., `sm:`, `md:`).
    *   Ensure the modal is fully responsive.
8.  **Testing and Iteration**:
    *   Verify correct event placement, rowspan behavior, and modal functionality.
    *   Test date filtering.
    *   Cross-browser testing.

## 7. Potential Challenges & Considerations

-   **Rowspan Logic**: Accurately rendering `<td>` elements with correct `rowspan` and skipping cells covered by a rowspan is complex. Pre-processing in Python is key to simplifying template logic.
-   **Performance**: For days with very many events and stages, the large HTML table could impact client-side rendering performance. If this occurs, more advanced solutions like virtual scrolling or pagination (by blocks of hours) might be needed, but start with the direct approach.
-   **Timezone Consistency**: Ensure all datetimes are handled consistently (e.g., stored in UTC, processed, and then displayed in the user's local time or a fixed festival timezone).
-   **Edge Cases**: Events starting/ending not exactly on 15-min intervals (round to nearest slot). Events shorter than 15 mins.

This comprehensive plan aims for a server-rendered HTML page enhanced with JavaScript, aligning with the existing application architecture while prioritizing a good user experience on both desktop and mobile. 