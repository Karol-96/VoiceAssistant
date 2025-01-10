// Full code example for Stripe payment integration

// Backend: Express.js Example
const express = require('express');
const bodyParser = require('body-parser');
const path = require('path');
const stripe = require('stripe')('sk_test_51Qej8uGL5dHVlQvazKNILTbUEfDaiEMDhQGuaR5F62wM9mmmxTwoTBs3mp7Y88m5I8eR1kpEDuB1f5fzjdTBr7q400Yzuz57l5');
const app = express();

// Middleware
app.use(express.static(__dirname));
app.use(bodyParser.json());


app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'test_payment.html'));
});
// Endpoint to create Payment Intent
app.post('/create-payment-intent', async (req, res) => {
  const { amount, currency } = req.body;

  try {
    const paymentIntent = await stripe.paymentIntents.create({
      amount, // Amount in smallest currency unit (e.g., cents for USD)
      currency,
    });

    res.status(200).send({
      clientSecret: paymentIntent.client_secret,
    });
  } catch (error) {
    console.error('Error creating payment intent:', error); // Add detailed error logging
    res.status(500).send({ 
      error: error.message,
      type: error.type,
      code: error.code 
    });
  }
});
// Webhook Endpoint to handle events
app.post('/webhook', express.raw({ type: 'application/json' }), (req, res) => {
  const sig = req.headers['stripe-signature'];

  try {
    const event = stripe.webhooks.constructEvent(
      req.body,
      sig,
      'your-webhook-signing-secret' // Replace with your Webhook Signing Secret
    );

    switch (event.type) {
      case 'payment_intent.succeeded':
        console.log('Payment succeeded:', event.data.object);
        break;
      case 'payment_intent.payment_failed':
        console.log('Payment failed:', event.data.object);
        break;
      default:
        console.log(`Unhandled event type ${event.type}`);
    }

    res.json({ received: true });
  } catch (err) {
    console.error(err);
    res.status(400).send(`Webhook Error: ${err.message}`);
  }
});

// Start server
app.listen(3000, () => console.log('Server running on port 3000'));
