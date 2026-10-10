package com.demo;

import com.demo.PaymentService;
import org.junit.Assert;
import org.junit.Test;

public class PaymentService_getMerchantId_Test_Normal_39 {


    @Test
    public void testGetMerchantIdReturnsConfiguredValue() {
        String expectedMerchantId = "MERCHANT_12345";
        PaymentService paymentService = new PaymentService(null, null, expectedMerchantId);

        String actualMerchantId = paymentService.getMerchantId();

        Assert.assertNotNull(actualMerchantId);
        Assert.assertEquals(expectedMerchantId, actualMerchantId);
    }

}
