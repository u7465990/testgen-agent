package com.demo;

import com.demo.PaymentService;
import com.demo.PaymentService.*;
import org.junit.Assert;
import org.junit.Test;

public class PaymentService_refund_Str_Dbl_Test_Boundary_37 {


    @Test
    public void testRefundWithNullCustomerId() {
        final boolean[] gatewayRefundCalled = new boolean[] { false };
        final boolean[] notifierCalled = new boolean[] { false };

        PaymentGateway gateway = new PaymentGateway() {
            @Override
            public void refund(String customerId, double amount) {
                gatewayRefundCalled[0] = true;
                Assert.assertNull(customerId);
                Assert.assertEquals(25.0, amount, 0.0);
            }

            @Override
            public boolean charge(String customerId, double amount) {
                return false;
            }
        };

        NotificationService notifier = new NotificationService() {
            @Override
            public void notify(String customerId, String message) {
                notifierCalled[0] = true;
                Assert.assertNull(customerId);
                Assert.assertEquals("Refunded 25.0", message);
            }
        };

        PaymentService service = new PaymentService(gateway, notifier, "merchant-1");

        service.refund(null, 25.0);

        Assert.assertTrue(gatewayRefundCalled[0]);
        Assert.assertTrue(notifierCalled[0]);
    }

}