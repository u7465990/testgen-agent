package com.demo;

/**
 * An external payment provider. Deliberately an interface so a unit test can
 * stand a mock in for it — see PaymentService, which depends on this.
 */
public interface PaymentGateway {

    /**
     * Charges a customer. Returns false when the provider declines.
     *
     * @throws IllegalStateException if the provider is unreachable
     */
    boolean charge(String customerId, double amount);

    /** Reverses a previously successful charge. */
    void refund(String customerId, double amount);
}
