package com.demo;

import com.demo.PaymentService;
import org.junit.Assert;
import org.junit.Test;

public class PaymentService_pay_Str_Dbl_Test_Normal_33 {


    @Test
    public void testPayWithNonPositiveAmounts() {
        PaymentService service = new PaymentService(null, null, "merchant-1");

        boolean thrownForNegative = false;
        try {
            service.pay("test", -1.0);
        } catch (IllegalArgumentException e) {
            thrownForNegative = true;
        }
        Assert.assertTrue("Expected IllegalArgumentException for amount -1.0", thrownForNegative);

        boolean thrownForZero = false;
        try {
            service.pay("", 0.0);
        } catch (IllegalArgumentException e) {
            thrownForZero = true;
        }
        Assert.assertTrue("Expected IllegalArgumentException for amount 0.0", thrownForZero);
    }

}
