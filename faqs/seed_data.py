"""Seed content for FAQs and the error-code reference.

Kept in one plain Python module so it is easy to review and to explain.
The `seed_faqs` management command loads it idempotently.
"""

FAQS = [
    {
        "category": "general",
        "question": "What does Gather & Co. do?",
        "answer": (
            "Gather & Co. is an event-rental inventory website. You can browse our catalogue of "
            "chairs, tables, tents, lighting, tableware and décor, check availability for your dates, "
            "and reserve items through an online booking. The owner reviews each booking and confirms it."
        ),
        "keywords": "about, website, purpose, rental, inventory, what is",
    },
    {
        "category": "bookings",
        "question": "How do I reserve an item?",
        "answer": (
            "Sign in (or create a free customer account), open a product from the Inventory page, choose "
            "your start date, end date and quantity, then press Reserve. The site checks live availability "
            "and gives you a booking reference such as BK-1A2B3C. Your booking starts as 'Pending review' "
            "until the owner confirms it."
        ),
        "keywords": "reserve, book, booking, reservation, rent, order, how to",
    },
    {
        "category": "bookings",
        "question": "How is availability calculated?",
        "answer": (
            "Each product has a total quantity in stock. For the dates you choose, the site adds up the units "
            "already held by pending or confirmed bookings that overlap those dates. You can reserve up to the "
            "remaining quantity. Declined and cancelled bookings release their units immediately."
        ),
        "keywords": "availability, available, stock, quantity, sold out, dates",
    },
    {
        "category": "bookings",
        "question": "Can I cancel or change a booking?",
        "answer": (
            "Yes. Open 'My bookings' and press Cancel on any pending or confirmed booking. To change dates or "
            "quantity, cancel the booking and make a new one, or create a support ticket and the owner will help."
        ),
        "keywords": "cancel, change, modify, edit booking, refund",
    },
    {
        "category": "bookings",
        "question": "How is the rental price calculated?",
        "answer": (
            "The estimated total is the item's daily rate × quantity × number of days (start and end dates are "
            "both counted). Payment is arranged with the owner after confirmation; the website does not take "
            "card payments."
        ),
        "keywords": "price, cost, rate, total, payment, pay, fee",
    },
    {
        "category": "general",
        "question": "Do I need an account to browse the inventory?",
        "answer": (
            "No. Anyone can browse the Inventory page, view product photos, prices and stock, read the FAQs and use "
            "the assistant. You only need a free customer account to reserve items and see your bookings."
        ),
        "keywords": "account, browse, guest, without account, need login, register",
    },
    {
        "category": "general",
        "question": "How do I create an account?",
        "answer": (
            "Click 'Create account' in the top navigation bar, choose a username, enter your first name, email address "
            "and a password (typed twice), then submit. You are signed in straight away and can start reserving items."
        ),
        "keywords": "sign up, signup, register, create account, make an account, new account, join",
    },
    {
        "category": "general",
        "question": "How do I sign in or sign out?",
        "answer": (
            "Use 'Sign in' in the navigation bar and enter your username and password. When signed in, the navigation "
            "bar shows 'My bookings' and a 'Sign out' button with your username. For testing, the sign-in page lists the "
            "demo customer and owner accounts."
        ),
        "keywords": "sign in, login, log in, logout, log out, sign out, demo account, password",
    },
    {
        "category": "general",
        "question": "What should I do if I forgot my password?",
        "answer": (
            "The website does not have a self-service password reset yet. Create a support ticket in the 'Account or "
            "login' category with your username and email address, and the owner can reset it from the admin area."
        ),
        "keywords": "forgot password, reset password, lost password, can't log in, locked out",
    },
    {
        "category": "general",
        "question": "What items can I rent?",
        "answer": (
            "The inventory is grouped into six categories: Seating (chairs and sofas), Tables, Tents & Canopies, "
            "Lighting, Tableware and Décor. Every item has a photo, a daily rate and the number of units in stock. "
            "Open the Inventory page to see the full, up-to-date list."
        ),
        "keywords": "what can i rent, items, products, rent, catalogue, catalog, categories, chairs, tables, tents, lighting, tableware, decor",
    },
    {
        "category": "general",
        "question": "How do I search the inventory and check availability for my dates?",
        "answer": (
            "On the Inventory page, type a word such as 'chair' or 'tent' in Search, optionally pick a Category, enter "
            "your From and To dates and press Apply. Each item then shows how many units are still available for those "
            "dates, or 'Fully booked'."
        ),
        "keywords": "search, filter, find item, check availability, dates, inventory page",
    },
    {
        "category": "bookings",
        "question": "What are the booking rules and limits?",
        "answer": (
            "The start date cannot be in the past, the end date must be on or after the start date, a booking can last "
            "at most 30 days, and you can book up to one year ahead. The quantity must be at least 1 and cannot exceed "
            "the units still available for those dates. Contact phone and event details are optional."
        ),
        "keywords": "rules, limits, maximum, minimum, how long, rent for, advance, days, quantity, dates",
    },
    {
        "category": "bookings",
        "question": "What do the booking statuses mean?",
        "answer": (
            "Pending review: your request was received and is waiting for the owner. Confirmed: the owner accepted it. "
            "Declined: the owner could not accept it. Cancelled by customer: you cancelled it. Completed: the rental "
            "has finished. Pending and confirmed bookings reserve stock; the others do not."
        ),
        "keywords": "status, pending, confirmed, declined, cancelled, completed, booking status, approved",
    },
    {
        "category": "bookings",
        "question": "Where can I see my bookings?",
        "answer": (
            "Sign in and click 'My bookings' in the navigation bar. Each booking shows the item, its reference (for "
            "example BK-1A2B3C), dates, quantity, estimated total, status and any note from the owner."
        ),
        "keywords": "my bookings, see bookings, view reservation, track, booking reference, history",
    },
    {
        "category": "bookings",
        "question": "Can I reserve several different items for one event?",
        "answer": (
            "Yes. Each booking is for one item, so make one booking per item (for example chairs, then tables, then "
            "lights) using the same dates. You can describe the event in the 'Event details' field so the owner sees "
            "they belong together."
        ),
        "keywords": "multiple items, several items, many items, cart, basket, combine, one event",
    },
    {
        "category": "bookings",
        "question": "What happens if an item is fully booked?",
        "answer": (
            "If too few units remain for your dates, the booking form tells you how many are available, or that the item "
            "is fully booked. Try different dates, a smaller quantity or a similar item. Units become available again "
            "when other bookings are declined or cancelled."
        ),
        "keywords": "fully booked, sold out, unavailable, not available, no stock, out of stock",
    },
    {
        "category": "bookings",
        "question": "Is my booking confirmed straight away?",
        "answer": (
            "No. New bookings start as 'Pending review' and already hold the units for your dates. The owner then "
            "confirms or declines the booking from the owner dashboard, and the new status appears in 'My bookings'."
        ),
        "keywords": "confirmed, confirmation, approve, instant, straight away, how long confirm, owner review",
    },
    {
        "category": "general",
        "question": "How does the owner post items and manage bookings?",
        "answer": (
            "The owner signs in with an owner account and opens the Owner dashboard. There they can see booking "
            "statistics, filter bookings by status, confirm, decline or complete bookings with a note, post new items "
            "with a photo, price and stock quantity, and edit or hide existing items."
        ),
        "keywords": "owner, admin, post item, add product, manage bookings, dashboard, upload photo, edit product",
    },
    {
        "category": "general",
        "question": "What personal data does the website store?",
        "answer": (
            "Your account stores your username, first name, email and a securely hashed password. Bookings store the "
            "item, dates, quantity and any optional phone number or event details you enter. Assistant conversations "
            "are logged with a random conversation ID rather than your name. Support tickets store only the details "
            "you type into the form."
        ),
        "keywords": "privacy, personal data, data stored, security, safe, gdpr, information",
    },
    {
        "category": "general",
        "question": "What is the weather card on the home page?",
        "answer": (
            "The 'Event-day weather' card shows live weather from OpenWeather to help you plan outdoor events, for "
            "example whether to add a tent. Type a city and press Check. If the weather service is unavailable, the "
            "card says so instead of showing made-up values."
        ),
        "keywords": "weather, forecast, temperature, rain, openweather, city",
    },
    {
        "category": "assistant",
        "question": "How does the AI assistant work?",
        "answer": (
            "The assistant first searches the FAQ records and error-code reference stored in our database for "
            "entries that match your question. Only those matching entries are sent to the AI model, which is "
            "instructed to answer using that information only. If nothing relevant is found, the assistant says "
            "so and offers to create a support ticket. When the AI provider is unavailable, you see the matching "
            "FAQ text directly, clearly labelled as a non-AI fallback."
        ),
        "keywords": "assistant, ai, chatbot, chat, bot, how does it work",
    },
    {
        "category": "general",
        "question": "What are FAQs?",
        "answer": (
            "FAQs (Frequently Asked Questions) are short, verified answers to the questions customers ask most "
            "often. Ours are stored in a PostgreSQL database, shown on the FAQ page, and used by the assistant "
            "as its knowledge base."
        ),
        "keywords": "faq, frequently asked questions, knowledge base",
    },
    {
        "category": "errors",
        "question": "How do HTTP status codes work?",
        "answer": (
            "Every web response carries a three-digit HTTP status code. 2xx means success, 3xx means redirection, "
            "4xx means the request had a problem (for example a missing page or missing permission), and 5xx means "
            "the server failed. Gather & Co. also uses one application code, 4600, which is not an HTTP status."
        ),
        "keywords": "http, status code, status codes, 2xx, 4xx, 5xx, error codes",
    },
    {
        "category": "errors",
        "question": "What does a 400 Bad Request error mean?",
        "answer": (
            "400 means the server could not accept the request because something in it was invalid, such as an "
            "empty question, a malformed form, an end date before the start date, or a message that is too long. "
            "Check the highlighted fields and try again."
        ),
        "keywords": "400, bad request, invalid, malformed",
    },
    {
        "category": "errors",
        "question": "What does a 401 Unauthorized error mean?",
        "answer": (
            "401 means you need to sign in first. On Gather & Co. you must be signed in to reserve items or view "
            "your bookings. Sign in and try again."
        ),
        "keywords": "401, unauthorized, sign in, login, log in, authentication",
    },
    {
        "category": "errors",
        "question": "What does a 403 Forbidden error mean?",
        "answer": (
            "403 means you are signed in but not allowed to do that action, or the security (CSRF) check failed. "
            "For example, customers cannot open the owner dashboard. Refresh the page and try again; if you "
            "believe you should have access, create a support ticket."
        ),
        "keywords": "403, forbidden, permission, access denied, csrf",
    },
    {
        "category": "errors",
        "question": "What does a 404 Not Found error mean?",
        "answer": (
            "404 means the page or item you asked for does not exist. The link may be mistyped, or a product may "
            "have been removed from the catalogue. Use the navigation bar or go back to the Inventory page."
        ),
        "keywords": "404, not found, missing page, broken link",
    },
    {
        "category": "errors",
        "question": "What does a 429 Too Many Requests error mean?",
        "answer": (
            "429 means you sent too many requests in a short time, so the site is temporarily slowing you down to "
            "protect the service. Wait about a minute and try again."
        ),
        "keywords": "429, too many requests, rate limit, slow down, throttled",
    },
    {
        "category": "support",
        "question": "How do I create a support ticket?",
        "answer": (
            "Open the Support page, fill in a subject and description (name and email are optional), choose a "
            "category and submit. You will see a ticket reference such as GC-1A2B3C4D. The assistant can also "
            "create a ticket for you when it cannot answer a question."
        ),
        "keywords": "support ticket, ticket, create ticket, report problem, help",
    },
    {
        "category": "support",
        "question": "How are support tickets stored?",
        "answer": (
            "Tickets are stored in our PostgreSQL database with a unique reference, subject, description, "
            "category, status and priority. Only authorised staff can view and manage them through the secure "
            "Django admin area; there is no public ticket dashboard."
        ),
        "keywords": "ticket storage, stored, database, privacy, ticket status",
    },
    {
        "category": "support",
        "question": "How do I contact support?",
        "answer": (
            "The fastest way is to create a ticket on the Support page and keep your ticket reference. Include "
            "your email address if you would like a reply. You can also ask the assistant first; it is "
            "available on every page."
        ),
        "keywords": "contact, email, phone, reach, support, help, human",
    },
]


ERROR_CODES = [
    {
        "code": 400,
        "name": "Bad Request",
        "kind": "http",
        "meaning": "The server could not process the request because it was invalid or incomplete.",
        "common_causes": "A required form field was left empty\nAn end date earlier than the start date\nA chat message longer than 500 characters\nMalformed JSON sent to the assistant",
        "troubleshooting": "Read the error message next to the form fields\nCorrect the highlighted values\nShorten very long messages\nRefresh the page and submit again",
        "next_action": "Fix the input and resubmit. If the form keeps rejecting valid input, create a support ticket.",
    },
    {
        "code": 401,
        "name": "Unauthorized",
        "kind": "http",
        "meaning": "The action requires you to be signed in.",
        "common_causes": "You are not signed in\nYour session expired\nYou opened a bookings link from another device",
        "troubleshooting": "Sign in using the button in the navigation bar\nCreate a customer account if you do not have one\nTry the action again after signing in",
        "next_action": "Sign in and retry. If you cannot sign in, create a support ticket in the Account category.",
    },
    {
        "code": 403,
        "name": "Forbidden",
        "kind": "http",
        "meaning": "You are not allowed to perform this action, even if you are signed in.",
        "common_causes": "A customer account trying to open the owner dashboard\nAn expired or missing CSRF security token\nTrying to view another customer's booking",
        "troubleshooting": "Refresh the page to get a fresh security token\nMake sure you are signed in with the correct account\nEnable cookies for this site",
        "next_action": "If you believe you should have access, create a support ticket explaining what you tried to do.",
    },
    {
        "code": 404,
        "name": "Not Found",
        "kind": "http",
        "meaning": "The requested page or item does not exist.",
        "common_causes": "A mistyped URL\nAn outdated bookmark\nA product that has been removed from the catalogue",
        "troubleshooting": "Check the address for typos\nUse the navigation bar to find the page\nSearch the Inventory page for the product",
        "next_action": "Return to the home page or ask the assistant to help you find what you need.",
    },
    {
        "code": 429,
        "name": "Too Many Requests",
        "kind": "http",
        "meaning": "Too many requests were sent in a short time, so the site is temporarily limiting you.",
        "common_causes": "Sending many chat messages very quickly\nSubmitting the same form repeatedly\nAutomated scripts calling the site",
        "troubleshooting": "Wait about 60 seconds\nAvoid double-clicking submit buttons\nTry again at a slower pace",
        "next_action": "Wait a minute and retry. If the limit appears during normal use, create a support ticket.",
    },
    {
        "code": 500,
        "name": "Internal Server Error",
        "kind": "http",
        "meaning": "Something went wrong on our server while handling the request. It is not caused by your input.",
        "common_causes": "An unexpected bug in the application\nA temporary database problem\nA failed deployment",
        "troubleshooting": "Refresh the page after a few seconds\nTry again later\nNote the time and what you were doing",
        "next_action": "If the error repeats, create a support ticket with the time and the page you were using.",
    },
    {
        "code": 503,
        "name": "Service Unavailable",
        "kind": "http",
        "meaning": "The service, or a service it depends on, is temporarily unavailable.",
        "common_causes": "The server is starting up or being redeployed\nThe database is temporarily unreachable\nPlanned maintenance",
        "troubleshooting": "Wait a minute and refresh\nCheck the /health/ endpoint status\nTry again later",
        "next_action": "Retry shortly. If the site stays unavailable for more than 15 minutes, create a support ticket.",
    },
    {
        "code": 4600,
        "name": "AI_ASSISTANT_UNAVAILABLE",
        "kind": "app",
        "meaning": (
            "A Gather & Co. application code (not an HTTP status) meaning the AI provider could not be reached "
            "or is not configured, so the assistant could not generate an AI answer."
        ),
        "common_causes": "The AI API key is not configured on the server\nThe AI provider timed out or returned an error\nThe AI provider's rate limit or quota was reached",
        "troubleshooting": "Read the FAQ-based fallback answer shown in the chat\nBrowse the FAQ and Error Code pages directly\nTry the assistant again in a few minutes",
        "next_action": "Use the FAQ fallback or create a support ticket; the rest of the website keeps working normally.",
    },
]
