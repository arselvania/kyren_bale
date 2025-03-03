Bale Group Buying Web Application - Technical Documentation

Overview

The Kairon Web App is a group-buying platform built on Bale messenger, allowing users to purchase products collectively and receive discounts based on the seller's predefined criteria. The platform consists of a React frontend and a Python backend, integrated with Bale's API.

Bale Integration

Bale API Documentation: Mini App | Bot API

A webhook is set up to handle interactions with Bale.

Users can access the web app through Bale's Mini Apps framework.

Functionality

Group Buying Mechanism

Product Listing: Sellers define products, discounts, and conditions.

Minimum buyers required for a discount.

Percentage discount based on group size.

Joining a Group Purchase:

Buyers pay 10% upfront to join a group.

Once the required number of units is reached, the group purchase is confirmed.

If a single buyer purchases all required units, the group is instantly confirmed.

Handling Incomplete Groups:

If a buyer withdraws at the payment stage, the group waits for the next participant.

If multiple groups are incomplete, users are rearranged based on registration order to form complete groups.

Order Completion & Shipping:

Upon group confirmation, the remaining balance is paid.

The seller ships the products.

Backend (Python)

Handles user authentication, product management, and transactions.

Webhook to receive events from Bale (e.g., user actions).

Manages group formation logic and payment status updates.

Frontend (React)

Mobile-first responsive design.

Dark/Light mode switch.

Navigation:

Header with a back button on each page.

Main menu with Home, Cart, Account, and Orders.

Pages:

Login/Register.

Product Listings.

Group Buying Overview.

Shopping Cart.

Payment Processing.

Seller Dashboard (Product Management, Order Management).

Summary

This platform leverages Bale's Mini Apps to provide a seamless group-buying experience. Users benefit from discounts by purchasing together, while sellers gain a structured way to manage sales and customer engagement.


kyren/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── products.py
│   │   │   ├── groups.py
│   │   │   ├── orders.py
│   │   │   ├── payments.py
│   │   │   └── webhooks.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   └── security.py
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   └── crud.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── bale.py
│   │   │   ├── group_manager.py
│   │   │   └── payment.py
│   │   ├── __init__.py
│   │   └── main.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── context/
│   │   ├── hooks/
│   │   ├── pages/
│   │   ├── styles/
│   │   ├── types/
│   │   ├── utils/
│   │   ├── App.tsx
│   │   └── index.tsx
│   ├── package.json
│   ├── tsconfig.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md


