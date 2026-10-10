package com.demo;

import com.demo.PasswordValidator;
import org.junit.Assert;
import org.junit.Test;

public class PasswordValidator_strength_Str_Test_Normal_30 {


    @Test
    public void testStrength_Normal() {
        PasswordValidator validator = new PasswordValidator();

        String result = validator.strength("test");

        Assert.assertNotNull(result);
        Assert.assertTrue("strong".equals(result) || "weak".equals(result));
    }

}
