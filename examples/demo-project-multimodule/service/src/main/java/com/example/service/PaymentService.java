package com.example.service;

import com.example.core.Money;
import com.example.core.PaymentGateway;

public class PaymentService {

    private final PaymentGateway gateway;

    public PaymentService(PaymentGateway gateway) {
        this.gateway = gateway;
    }

    public boolean charge(String accountId, long cents) {
        if (cents <= 0) {
            throw new IllegalArgumentException("cents must be positive");
        }
        if (accountId == null || accountId.isEmpty()) {
            return false;
        }
        return gateway.charge(accountId, new Money(cents));
    }

    public String describe(boolean charged) {
        return charged ? "charged" : "declined";
    }
}
