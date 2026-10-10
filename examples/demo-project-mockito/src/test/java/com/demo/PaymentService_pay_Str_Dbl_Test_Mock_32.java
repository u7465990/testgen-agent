package com.demo;

import com.demo.PaymentService;
import org.junit.Assert;
import org.junit.Test;
import org.mockito.ArgumentMatchers;
import org.mockito.Mockito;

public class PaymentService_pay_Str_Dbl_Test_Mock_32 {

    @Test
    public void testPayWithMockedCollaborators() {
        com.demo.PaymentGateway gateway = Mockito.mock(com.demo.PaymentGateway.class);
        com.demo.NotificationService notifier = Mockito.mock(com.demo.NotificationService.class);
        PaymentService service = new PaymentService(gateway, notifier, "merchant-1");

        Mockito.when(gateway.charge(ArgumentMatchers.anyString(), ArgumentMatchers.anyDouble())).thenReturn(true);

        boolean result = service.pay("customer-1", 500.0);

        Assert.assertTrue(result);
        Mockito.verify(gateway).charge("customer-1", 500.0);
        Mockito.verify(notifier).notify("customer-1", "Charged 500.0");
    }

}
