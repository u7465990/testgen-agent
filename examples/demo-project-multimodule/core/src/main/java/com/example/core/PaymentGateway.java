package com.example.core;

/**
 * A collaborator the service module depends on. Tests for PaymentService must
 * mock this rather than construct it.
 */
public interface PaymentGateway {

    boolean charge(String accountId, Money amount);

    Money refund(String accountId, long cents);
}
