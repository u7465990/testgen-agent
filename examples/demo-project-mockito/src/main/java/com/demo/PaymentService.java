package com.demo;

/**
 * Takes two injected collaborators, so a unit test for this class has to mock
 * them — there is no way to exercise {@link #pay} against a real gateway.
 *
 * This is the class testgen-agent's [Mock] targets exist for: the branches in
 * {@code pay} depend on what {@code gateway.charge} returns, so a stub
 * (`when(gateway.charge(...)).thenReturn(true/false)`) is genuinely required
 * rather than decorative.
 */
public class PaymentService {

    private final PaymentGateway gateway;
    private final NotificationService notifier;
    private final String merchantId;

    public PaymentService(PaymentGateway gateway,
                          NotificationService notifier,
                          String merchantId) {
        this.gateway = gateway;
        this.notifier = notifier;
        this.merchantId = merchantId;
    }

    /**
     * Charges a customer through the gateway and notifies them of the result.
     *
     * @return true when the charge succeeded
     * @throws IllegalArgumentException if the amount is not positive
     */
    public boolean pay(String customerId, double amount) {
        if (amount <= 0) {
            throw new IllegalArgumentException("Amount must be positive");
        }
        if (amount > 10000) {
            notifier.notify(customerId, "Amount requires review");
            return false;
        }
        boolean charged = gateway.charge(customerId, amount);
        notifier.notify(customerId, charged ? "Charged " + amount
                                            : "Charge failed");
        return charged;
    }

    /** Total refunded so far, delegated to the gateway. */
    public void refund(String customerId, double amount) {
        if (amount <= 0) {
            throw new IllegalArgumentException("Refund must be positive");
        }
        gateway.refund(customerId, amount);
        notifier.notify(customerId, "Refunded " + amount);
    }

    public String getMerchantId() {
        return merchantId;
    }
}
