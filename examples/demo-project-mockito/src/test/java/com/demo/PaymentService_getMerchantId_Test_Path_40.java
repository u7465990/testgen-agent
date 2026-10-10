package com.demo;

import com.demo.PaymentService;
import org.junit.Assert;
import org.junit.Test;

public class PaymentService_getMerchantId_Test_Path_40 {


    @Test
    public void testGetMerchantIdReturnsConstructorValue() {
        String expectedMerchantId = "merchant-123";
        PaymentService paymentService = new PaymentService(null, null, expectedMerchantId);

        String actualMerchantId = paymentService.getMerchantId();

        Assert.assertEquals(expectedMerchantId, actualMerchantId);
    }

}
