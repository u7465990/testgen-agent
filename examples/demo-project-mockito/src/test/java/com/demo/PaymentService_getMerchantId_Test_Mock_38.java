package com.demo;

import com.demo.PaymentService;
import com.demo.PaymentGateway;
import com.demo.NotificationService;
import org.junit.Assert;
import org.junit.Test;
import org.mockito.ArgumentMatchers;
import org.mockito.Mockito;

public class PaymentService_getMerchantId_Test_Mock_38 {


    @Test
    public void testGetMerchantIdReturnsConstructorValue() {
        PaymentGateway gateway = Mockito.mock(PaymentGateway.class);
        NotificationService notifier = Mockito.mock(NotificationService.class);

        Mockito.when(gateway.charge(ArgumentMatchers.anyString(), ArgumentMatchers.anyDouble()))
                .thenReturn(true);
        Mockito.doNothing().when(notifier)
                .notify(ArgumentMatchers.anyString(), ArgumentMatchers.anyString());

        String merchantId = "merchant-42";
        PaymentService service = new PaymentService(gateway, notifier, merchantId);

        String result = service.getMerchantId();

        Assert.assertEquals("merchant-42", result);
        Mockito.verify(gateway, Mockito.never())
                .charge(ArgumentMatchers.anyString(), ArgumentMatchers.anyDouble());
        Mockito.verify(notifier, Mockito.never())
                .notify(ArgumentMatchers.anyString(), ArgumentMatchers.anyString());
    }

}
