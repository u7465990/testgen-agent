package com.demo;

/** Outbound notifications. Also an interface, like PaymentGateway. */
public interface NotificationService {

    void notify(String recipient, String message);
}
