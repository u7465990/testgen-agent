package com.demo;

import com.demo.PaymentService;
import org.junit.Assert;
import org.junit.Test;
import org.mockito.ArgumentMatchers;
import org.mockito.Mockito;

public class PaymentService_refund_Str_Dbl_Test_Mock_35 {


    @Test
    public void testRefund_notifiesAndCallsGatewayWithSameArguments() {
        com.demo.PaymentGateway gateway = Mockito.mock(com.demo.PaymentGateway.class);
        com.demo.NotificationService notifier = Mockito.mock(com.demo.NotificationService.class);
        Mockito.when(gateway.charge(ArgumentMatchers.anyString(), ArgumentMatchers.anyDouble()))
                .thenReturn(true);

        PaymentService service = new PaymentService(gateway, notifier, "merchant-42");
        Assert.assertNotNull(service);

        service.refund("customer-1", 25.5);

        Mockito.verify(gateway).refund(ArgumentMatchers.eq("customer-1"), ArgumentMatchers.eq(25.5));
        Mockito.verify(notifier).notify(ArgumentMatchers.eq("customer-1"), ArgumentMatchers.eq("Refunded 25.5"));
        Mockito.verifyNoMoreInteractions(gateway, notifier);
    }

}
