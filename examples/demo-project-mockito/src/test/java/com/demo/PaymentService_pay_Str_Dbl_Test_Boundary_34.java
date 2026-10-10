package com.demo;

import com.demo.PaymentService;
import org.junit.Assert;
import org.junit.Test;

public class PaymentService_pay_Str_Dbl_Test_Boundary_34 {


    @Test
    public void testPayWithNullCustomerIdBoundary() {
        PaymentGateway gateway = new PaymentGateway() {
            @Override
            public boolean charge(String customerId, double amount) {
                return true;
            }

            @Override
            public void refund(String customerId, double amount) {
                // no-op
            }
        };

        NotificationService notifier = new NotificationService() {
            @Override
            public void notify(String customerId, String message) {
                // no-op
            }
        };

        PaymentService service = new PaymentService(gateway, notifier, "merchant-1");

        boolean result = service.pay(null, 100.0);

        Assert.assertTrue("A null customerId should be forwarded and a successful charge should return true", result);
    }

}